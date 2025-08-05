from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import tweepy
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

load_dotenv()  # Always load the environment variables

class TwitterSearchLiteTool(BaseTool):
    """
    A lightweight, quota-conscious Twitter search tool designed for users with limited API access.
    This tool is optimized for accounts with restricted monthly post limits (e.g., 100 posts/month).
    It fetches exactly the requested number of tweets and provides essential engagement metrics.
    Perfect for users who need Twitter data but must conserve their API quota.
    """
    
    # Define the fields with descriptions using Pydantic Field
    topic_or_keywords: str = Field(
        ..., 
        description="The search query in natural language, keywords, or hashtags. Keep it simple for better quota efficiency. Examples: 'AI', '#technology', 'machine learning'."
    )
    
    max_results: int = Field(
        10, 
        description="Number of tweets to fetch (between 10-25, default: 10). Uses exactly this many API quota posts. Conservative default for quota preservation - API minimum is 10."
    )
    
    min_engagement_threshold: Optional[int] = Field(
        None, 
        description="Optional minimum total engagement score (likes + retweets + replies). If set, may result in fewer tweets returned if most don't meet threshold."
    )

    def run(self):
        """
        The implementation of the run method optimized for quota conservation.
        Fetches exactly the requested number of posts with minimal API parameters.
        """
        try:
            # Step 1: Validate inputs for lite version
            self._validate_inputs()
            
            # Step 2: Get Twitter Bearer Token from environment
            bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
            if not bearer_token:
                return json.dumps({
                    "error": "Twitter Bearer Token not found. Please set TWITTER_BEARER_TOKEN in your .env file.",
                    "query": self.topic_or_keywords,
                    "quota_used": 0,
                    "total_results": 0,
                    "tweets": []
                })
            
            # Step 3: Initialize Twitter API client
            client = tweepy.Client(bearer_token=bearer_token)
            
            # Step 4: Create simple, efficient query
            query = self._create_lite_query(self.topic_or_keywords)
            
            # Step 5: Calculate date range (last 3 days for efficiency)
            end_time = datetime.now(timezone.utc) - timedelta(seconds=30)
            start_time = end_time - timedelta(days=3)  # Shorter range for lite version
            
            # Step 6: Search tweets with minimal parameters
            tweets_data = self._search_tweets_lite(
                client, query, start_time, end_time
            )
            
            # Step 7: Process tweets with basic engagement calculation
            processed_tweets = self._process_tweets_lite(tweets_data)
            
            # Step 8: Filter by engagement threshold if specified
            if self.min_engagement_threshold:
                processed_tweets = [
                    tweet for tweet in processed_tweets 
                    if tweet["engagement_metrics"]["total_engagement"] >= self.min_engagement_threshold
                ]
            
            # Step 9: Return results with quota usage info
            result = {
                "query": self.topic_or_keywords,
                "quota_used": len(tweets_data),  # Actual API posts consumed
                "total_results": len(processed_tweets),
                "search_metadata": {
                    "search_time": datetime.now(timezone.utc).isoformat(),
                    "time_range": "last_3_days",
                    "lite_query": query,
                    "engagement_threshold": self.min_engagement_threshold,
                    "quota_warning": f"Used {len(tweets_data)} posts from your monthly quota"
                },
                "tweets": processed_tweets
            }
            
            return json.dumps(result, indent=2)
            
        except tweepy.TooManyRequests as e:
            return json.dumps({
                "error": "Twitter API rate limit exceeded. Please wait 15 minutes before trying again.",
                "rate_limit_info": "Your account may have very restrictive rate limits due to quota restrictions.",
                "query": self.topic_or_keywords,
                "quota_used": 0,
                "search_metadata": {
                    "search_time": datetime.now(timezone.utc).isoformat(),
                    "time_range": "last_3_days",
                    "lite_query": self._create_lite_query(self.topic_or_keywords if hasattr(self, 'topic_or_keywords') else ""),
                    "engagement_threshold": self.min_engagement_threshold
                },
                "total_results": 0,
                "tweets": []
            })
            
        except tweepy.Unauthorized:
            return json.dumps({
                "error": "Twitter API authentication failed. Please check your Bearer Token.",
                "query": self.topic_or_keywords,
                "quota_used": 0,
                "total_results": 0,
                "tweets": []
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"Unexpected error: {str(e)}",
                "query": self.topic_or_keywords,
                "quota_used": 0,
                "total_results": 0,
                "tweets": []
            })

    def _validate_inputs(self):
        """Validate inputs for lite version with stricter limits"""
        if not self.topic_or_keywords.strip():
            raise ValueError("Topic or keywords cannot be empty")
        
        if self.max_results < 10 or self.max_results > 25:
            raise ValueError("max_results must be between 10 and 25 for lite version (API minimum is 10)")
        
        if len(self.topic_or_keywords) > 100:
            raise ValueError("Query too long for lite version. Keep under 100 characters.")

    def _create_lite_query(self, query: str) -> str:
        """Create a simple, efficient query for quota conservation"""
        # Remove extra spaces and limit length
        query = query.strip()[:80]
        
        # Add basic filters for efficiency (optional)
        if not any(op in query for op in ['lang:', '-is:', 'from:', 'to:']):
            # Only add lang filter if no advanced operators present
            query = f"{query} lang:en"
        
        return query

    def _search_tweets_lite(self, client: tweepy.Client, query: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Search tweets with minimal API parameters for quota efficiency"""
        tweets_data = []
        
        try:
            # Minimal API call - only essential fields
            response = client.search_recent_tweets(
                query=query,
                start_time=start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                end_time=end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                tweet_fields=["created_at", "author_id", "public_metrics"],  # Minimal fields
                max_results=min(100, self.max_results)  # Exactly what user requested
            )
            
            if not response.data:
                return tweets_data
            
            # Process tweets with basic author info
            for tweet in response.data:
                tweet_data = {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_id": tweet.author_id,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "public_metrics": tweet.public_metrics or {}
                }
                tweets_data.append(tweet_data)
                
        except Exception as e:
            print(f"Error searching tweets: {e}")
            
        return tweets_data

    def _process_tweets_lite(self, tweets_data: List[Dict]) -> List[Dict]:
        """Process tweets with basic engagement calculation"""
        processed_tweets = []
        
        for tweet_data in tweets_data:
            metrics = tweet_data.get("public_metrics", {})
            
            # Calculate total engagement
            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)
            replies = metrics.get("reply_count", 0)
            quotes = metrics.get("quote_count", 0)
            total_engagement = likes + retweets + replies + quotes
            
            # Create basic tweet URL (without username lookup to save quota)
            tweet_url = f"https://x.com/i/status/{tweet_data['id']}"
            
            processed_tweet = {
                "id": str(tweet_data["id"]),
                "text": tweet_data["text"],
                "author_id": str(tweet_data["author_id"]),
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
    tool = TwitterSearchLiteTool(
        topic_or_keywords="AI",
        max_results=10,
        min_engagement_threshold=10
    )
    print(tool.run()) 