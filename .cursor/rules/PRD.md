# Social Media Analytics Agency

---

- **TwitterSearchTool:**
    - **Description**: A tool that searches and fetches the most engaged tweets on Twitter/X for specific topics or keywords. It searches within the last 6.5 days (optimized for free tier limits) and ranks tweets by total engagement (likes + retweets + replies + quotes). The tool is designed to help users identify highly engaging content around specific topics for market research, content inspiration, and competitive analysis.
    - **Inputs**:
        - topic_or_keywords (str) - The search query in natural language, keywords, hashtags, or phrases. Supports: simple keywords ("artificial intelligence"), exact phrases ("machine learning"), hashtags (#AI), mentions (@username), or combinations. Max 512 characters for Basic access.
        - max_results (int) - Number of tweets to fetch (between 10-100, default: 50)
        - min_engagement_threshold (int, optional) - Minimum total engagement score (likes + retweets + replies + quotes) to filter tweets. If not provided, tool fetches top engaged tweets without filtering
    - **Validation**:
        - topic_or_keywords must not be empty and under 512 characters - ensures valid search query within API limits
        - max_results must be between 10 and 100 - respects API rate limits and provides meaningful results
        - min_engagement_threshold must be positive integer if provided - ensures valid engagement filtering
        - Bearer token must be available in environment variables - ensures API authentication
    - **Core Functions:** 
        - Accept natural language queries and enhance them for optimal search results (add lang:en for English, -is:retweet to focus on original content)
        - Search recent tweets (last 6.5 days) using Twitter API v2 search endpoints with optimized query parameters
        - Fetch tweet metadata including text, author, URL, timestamp, and engagement metrics (public_metrics)
        - Calculate engagement score (likes + retweets + replies + quotes) for each tweet
        - Sort tweets by engagement score in descending order
        - Filter tweets by minimum engagement threshold if specified
        - Return structured JSON data with tweet details and metrics
        - Handle API rate limits (300 requests per 15-min window) and pagination automatically
        - Provide error handling, query validation, and fallback responses
    - **APIs**: 
        - Twitter API v2 (Search Posts endpoint: https://api.x.com/2/tweets/search/recent)
        - Uses Bearer Token authentication (OAuth 2.0 App-Only)
        - Tweepy Python library for Twitter API integration
        - Fields requested: public_metrics, created_at, author_id, text
        - Expansions requested: author_id (to get username)
    - **Output**: JSON object containing an array of tweet data with the following structure:
        ```json
        {
            "query": "search topic",
            "total_results": 25,
            "search_metadata": {
                "search_time": "2024-01-15T10:30:00Z",
                "time_range": "last_6.5_days",
                "engagement_threshold": 100
            },
            "tweets": [
                {
                    "id": "1234567890",
                    "text": "Tweet content...",
                    "author": {
                        "id": "author_id",
                        "username": "username"
                    },
                    "url": "https://x.com/username/status/1234567890",
                    "created_at": "2024-01-14T15:30:00Z",
                                         "engagement_metrics": {
                         "likes": 150,
                         "retweets": 45,
                         "replies": 20,
                         "quotes": 5,
                         "total_engagement": 220
                     }
                }
            ]
        }
                ```

- **TwitterSearchLiteTool:**
    - **Description**: A lightweight, quota-conscious Twitter search tool designed for users with limited API access (e.g., 100 posts/month free tier). It fetches exactly the requested number of tweets with minimal API parameters to preserve quota while providing essential engagement metrics. Optimized for sustainable, long-term usage with conservative defaults and efficient API calls.
    - **Inputs**:
        - topic_or_keywords (str) - The search query in natural language, keywords, or hashtags. Keep simple for better quota efficiency. Examples: 'AI', '#technology', 'machine learning'.
        - max_results (int) - Number of tweets to fetch (between 10-25, default: 10). Uses exactly this many API quota posts for conservative quota management.
        - min_engagement_threshold (int, optional) - Optional minimum total engagement score (likes + retweets + replies + quotes). If set, may result in fewer tweets returned if most don't meet threshold.
    - **Validation**:
        - topic_or_keywords must not be empty and under 100 characters - ensures valid, efficient search query
        - max_results must be between 10 and 25 - respects API minimum and strict quota limits while providing meaningful results
        - min_engagement_threshold must be positive integer if provided - ensures valid engagement filtering
        - Bearer token must be available in environment variables - ensures API authentication
    - **Core Functions:** 
        - Accept simple search queries with basic enhancement (lang:en filter only)
        - Search recent tweets (last 3 days) using minimal API parameters for efficiency
        - Fetch essential tweet metadata: text, author_id, URL, timestamp, and engagement metrics
        - Calculate engagement score (likes + retweets + replies + quotes) for each tweet
        - Sort tweets by engagement score in descending order
        - Filter tweets by minimum engagement threshold if specified
        - Return structured JSON data with quota usage tracking
        - Provide quota usage warnings and efficient error handling
        - Skip username lookups to save API calls
    - **APIs**: 
        - Twitter API v2 (Search Posts endpoint: https://api.x.com/2/tweets/search/recent)
        - Uses Bearer Token authentication (OAuth 2.0 App-Only)
        - Tweepy Python library for Twitter API integration
        - Minimal fields requested: public_metrics, created_at, author_id, text (no expansions)
        - No username lookups to preserve quota
    - **Output**: JSON object containing an array of tweet data with quota tracking:
        ```json
        {
            "query": "AI",
            "quota_used": 10,
            "total_results": 10,
            "search_metadata": {
                "search_time": "2024-01-15T10:30:00Z",
                "time_range": "last_3_days",
                "lite_query": "AI lang:en",
                "engagement_threshold": 50,
                "quota_warning": "Used 10 posts from your monthly quota"
            },
            "tweets": [
                {
                    "id": "1234567890",
                    "text": "Tweet content...",
                    "author_id": "44196397",
                    "url": "https://x.com/i/status/1234567890",
                    "created_at": "2024-01-14T15:30:00Z",
                    "engagement_metrics": {
                        "likes": 150,
                        "retweets": 45,
                        "replies": 20,
                        "quotes": 5,
                        "total_engagement": 220
                    }
                }
            ]
        }
        ```

- **YouTubeSearchTool:**
    - **Description**: A tool that searches and fetches the most engaged YouTube videos for specific topics or keywords. It searches within the last week and ranks videos by total engagement (views + likes + comments). The tool is designed to help users identify highly engaging video content around specific topics for market research, content inspiration, and competitive analysis. Limited to 100 searches per day due to free tier quota constraints.
    - **Inputs**:
        - topic_or_keywords (str) - The search query in natural language, keywords, hashtags, or phrases. Supports: simple keywords ("artificial intelligence"), exact phrases ("machine learning"), hashtags (#AI), Boolean operators (AND, OR, NOT), or combinations.
        - max_results (int) - Number of videos to fetch (between 10-50, default: 25)
        - min_engagement_threshold (int, optional) - Minimum total engagement score (views + likes + comments) to filter videos. If not provided, tool fetches top engaged videos without filtering
    - **Validation**:
        - topic_or_keywords must not be empty - ensures valid search query
        - max_results must be between 10 and 50 - respects API quota limits and provides meaningful results
        - min_engagement_threshold must be positive integer if provided - ensures valid engagement filtering
        - API key must be available in environment variables - ensures API authentication
    - **Core Functions:** 
        - Accept natural language queries and enhance them for optimal search results (add lang:en for English)
        - Search recent videos (last week) using YouTube Data API v3 search endpoint
        - Fetch video statistics using videos.list endpoint to get engagement metrics
        - Calculate engagement score (views + likes + comments) for each video - Note: dislikes deprecated in 2021
        - Sort videos by engagement score in descending order
        - Filter videos by minimum engagement threshold if specified
        - Return structured JSON data with video details and metrics
        - Handle API quota limits (100 units per search + 1 unit per video details call)
        - Provide error handling and fallback responses
        - Optimize API usage by batching video details requests
    - **APIs**: 
        - YouTube Data API v3 (search.list endpoint costs 100 units, videos.list endpoint costs 1 unit per video)
        - Uses API Key authentication
        - google-api-python-client Python library for YouTube API integration
        - Fields requested: snippet, statistics, contentDetails
    - **Output**: JSON object containing an array of video data with the following structure:
        ```json
        {
            "query": "search topic",
            "total_results": 25,
            "search_metadata": {
                "search_time": "2024-01-15T10:30:00Z",
                "time_range": "last_6.5_days",
                "engagement_threshold": 1000,
                "quota_used": 125
            },
            "videos": [
                {
                    "id": "video_id",
                    "title": "Video title...",
                    "description": "Video description...",
                    "channel_title": "Channel Name",
                    "url": "https://www.youtube.com/watch?v=video_id",
                    "published_at": "2024-01-14T15:30:00Z",
                    "duration": "PT10M30S",
                    "thumbnail_url": "https://i.ytimg.com/vi/video_id/hqdefault.jpg",
                    "engagement_metrics": {
                        "views": 15000,
                        "likes": 1500,
                        "comments": 200,
                        "total_engagement": 16700
                    }
                }
            ]
        }
        ```