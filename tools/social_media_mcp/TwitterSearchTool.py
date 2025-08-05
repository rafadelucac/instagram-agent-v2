from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import tweepy
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

load_dotenv()  # Always load the environment variables

class TwitterSearchTool(BaseTool):
    """
    A tool that searches and fetches the most engaged tweets on Twitter/X for specific topics or keywords.
    It searches within the last week and ranks tweets by total engagement (likes + retweets + replies + quotes).
    The tool is designed to help users identify highly engaging content around specific topics for market research,
    content inspiration, and competitive analysis.
    """
    
    # Define the fields with descriptions using Pydantic Field
    topic_or_keywords: str = Field(
        ..., 
        description="The search query in natural language, keywords, hashtags, or phrases. Supports: simple keywords (artificial intelligence), exact phrases (machine learning), hashtags (#AI), mentions (@username), or combinations. Max 512 characters for Basic access."
    )
    
    max_results: int = Field(
        50, 
        description="Number of tweets to fetch (between 10-100, default: 50). Tool fetches exactly this number from API and sorts by engagement. Higher numbers use more API quota."
    )
    
    min_engagement_threshold: Optional[int] = Field(
        None, 
        description="Optional minimum total engagement score (likes + retweets + replies + quotes) to filter tweets. If not provided, tool fetches top engaged tweets without filtering."
    )

    def run(self):
        """
        The implementation of the run method, where the tool's main functionality is executed.
        This method utilizes the fields defined above to perform the Twitter search and analysis.
        """
        try:
            # Step 1: Validate inputs
            self._validate_inputs()
            
            # Step 2: Get Twitter Bearer Token from environment
            bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
            if not bearer_token:
                return json.dumps({
                    "error": "Twitter Bearer Token not found. Please set TWITTER_BEARER_TOKEN in your .env file.",
                    "query": self.topic_or_keywords,
                    "total_results": 0,
                    "tweets": []
                })
            
            # Step 3: Initialize Twitter API client
            client = tweepy.Client(bearer_token=bearer_token)
            
            # Step 4: Enhance query for better results
            enhanced_query = self._enhance_query(self.topic_or_keywords)
            
            # Step 5: Calculate date range (last week with safety margins)
            # Twitter API requires end_time to be at least 10 seconds before request time
            end_time = datetime.now(timezone.utc) - timedelta(seconds=30)  # 30 seconds buffer
            # Use 6.5 days instead of 7 to avoid hitting free tier time limits
            start_time = end_time - timedelta(days=6, hours=12)  # 6.5 days with buffer
            
            # Step 6: Search tweets using Twitter API v2
            tweets_data = self._search_tweets(
                client, enhanced_query, start_time, end_time
            )
            
            # Step 7: Process and rank tweets by engagement
            processed_tweets = self._process_tweets(tweets_data)
            
            # Step 8: Filter by engagement threshold if specified
            if self.min_engagement_threshold:
                processed_tweets = [
                    tweet for tweet in processed_tweets 
                    if tweet["engagement_metrics"]["total_engagement"] >= self.min_engagement_threshold
                ]
            
            # Step 9: Limit to requested number of results
            final_tweets = processed_tweets[:self.max_results]
            
            # Step 10: Return structured JSON response
            result = {
                "query": self.topic_or_keywords,
                "total_results": len(final_tweets),
                "search_metadata": {
                    "search_time": datetime.now(timezone.utc).isoformat(),
                    "time_range": "last_6.5_days",
                    "enhanced_query": enhanced_query,
                    "engagement_threshold": self.min_engagement_threshold
                },
                "tweets": final_tweets
            }
            
            return json.dumps(result, indent=2)
            
        except tweepy.TooManyRequests as e:
            return json.dumps({
                "error": "Twitter API rate limit exceeded. Please wait 15 minutes before trying again.",
                "rate_limit_info": str(e),
                "query": self.topic_or_keywords,
                "search_metadata": {
                    "search_time": datetime.now(timezone.utc).isoformat(),
                    "time_range": "last_6.5_days",
                    "enhanced_query": self._enhance_query(self.topic_or_keywords),
                    "engagement_threshold": self.min_engagement_threshold
                },
                "total_results": 0,
                "tweets": []
            })
            
        except tweepy.Unauthorized:
            return json.dumps({
                "error": "Twitter API authentication failed. Please check your Bearer Token.",
                "query": self.topic_or_keywords,
                "total_results": 0,
                "tweets": []
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"An error occurred: {str(e)}",
                "query": self.topic_or_keywords,
                "search_metadata": {
                    "search_time": datetime.now(timezone.utc).isoformat(),
                    "time_range": "last_6.5_days",
                    "enhanced_query": self._enhance_query(self.topic_or_keywords) if hasattr(self, 'topic_or_keywords') else "",
                    "engagement_threshold": self.min_engagement_threshold
                },
                "total_results": 0,
                "tweets": []
            })

    def _validate_inputs(self):
        """Validate the input parameters"""
        if not self.topic_or_keywords or len(self.topic_or_keywords.strip()) == 0:
            raise ValueError("topic_or_keywords cannot be empty")
        
        if len(self.topic_or_keywords) > 512:
            raise ValueError("topic_or_keywords must be under 512 characters for Basic API access")
        
        if not 10 <= self.max_results <= 100:
            raise ValueError("max_results must be between 10 and 100")
        
        if self.min_engagement_threshold is not None and self.min_engagement_threshold < 0:
            raise ValueError("min_engagement_threshold must be a positive integer")

    def _enhance_query(self, query: str) -> str:
        """Enhance the query for better search results"""
        # Add language filter for English tweets and exclude retweets for original content
        enhanced = f"{query} lang:en -is:retweet"
        
        # Ensure query doesn't exceed character limit
        if len(enhanced) > 512:
            # If enhanced query is too long, use original query with just language filter
            enhanced = f"{query} lang:en"
            if len(enhanced) > 512:
                # If still too long, use original query only
                enhanced = query
        
        return enhanced

    def _search_tweets(self, client: tweepy.Client, query: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Search tweets using Twitter API v2"""
        tweets_data = []
        
        try:
            # Search for tweets with a single request first
            response = client.search_recent_tweets(
                query=query,
                start_time=start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                end_time=end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                tweet_fields=["created_at", "author_id", "public_metrics"],
                expansions=["author_id"],
                user_fields=["username", "name"],
                max_results=min(100, self.max_results)  # Fetch exactly what user requested
            )
            
            if not response.data:
                return tweets_data
            
            # Extract user information from includes
            users_map = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    users_map[user.id] = {
                        "id": user.id,
                        "username": user.username,
                        "name": user.name
                    }
            
            # Process tweets
            for tweet in response.data:
                # Get user info
                author_info = users_map.get(tweet.author_id, {
                    "id": tweet.author_id,
                    "username": "unknown",
                    "name": "Unknown User"
                })
                
                tweet_data = {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author": author_info,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "public_metrics": tweet.public_metrics or {}
                }
                tweets_data.append(tweet_data)
                
        except Exception as e:
            print(f"Error searching tweets: {e}")
            # Return empty list if search fails
            
        return tweets_data

    def _process_tweets(self, tweets_data: List[Dict]) -> List[Dict]:
        """Process tweets and calculate engagement scores"""
        processed_tweets = []
        
        for tweet_data in tweets_data:
            metrics = tweet_data.get("public_metrics", {})
            
            # Calculate total engagement (likes + retweets + replies + quotes)
            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)
            replies = metrics.get("reply_count", 0)
            quotes = metrics.get("quote_count", 0)
            total_engagement = likes + retweets + replies + quotes
            
            # Create tweet URL
            username = tweet_data["author"].get("username", "unknown")
            tweet_url = f"https://x.com/{username}/status/{tweet_data['id']}"
            
            processed_tweet = {
                "id": str(tweet_data["id"]),
                "text": tweet_data["text"],
                "author": tweet_data["author"],
                "url": tweet_url,
                "created_at": tweet_data["created_at"],
                "engagement_metrics": {
                    "likes": likes,
                    "retweets": retweets,
                    "replies": replies,
                    "quotes": quotes,
                    "total_engagement": total_engagement
                }
            }
            
            processed_tweets.append(processed_tweet)
        
        # Sort by total engagement in descending order
        processed_tweets.sort(
            key=lambda x: x["engagement_metrics"]["total_engagement"], 
            reverse=True
        )
        
        return processed_tweets

if __name__ == "__main__":
    # Test case for the tool
    tool = TwitterSearchTool(
        topic_or_keywords="artificial intelligence",
        max_results=20,
        min_engagement_threshold=50
    )
    print(tool.run()) 