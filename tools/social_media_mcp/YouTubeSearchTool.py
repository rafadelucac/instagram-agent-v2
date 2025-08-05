from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import isodate

load_dotenv()  # Always load the environment variables

class YouTubeSearchTool(BaseTool):
    """
    A tool that searches and fetches the most engaged YouTube videos for specific topics or keywords.
    It searches within the last week and ranks videos by total engagement (views + likes + comments).
    The tool is designed to help users identify highly engaging video content around specific topics
    for market research, content inspiration, and competitive analysis.
    Limited to 100 searches per day due to free tier quota constraints.
    """
    
    topic_or_keywords: str = Field(
        ..., 
        description="The search query in natural language, keywords, hashtags, or phrases. Supports: simple keywords (\"artificial intelligence\"), exact phrases (\"machine learning\"), hashtags (#AI), Boolean operators (AND, OR, NOT), or combinations."
    )
    
    max_results: int = Field(
        25, 
        description="Number of videos to fetch (between 10-50, default: 25)",
        ge=10,  # Minimum 10
        le=50   # Maximum 50
    )
    
    min_engagement_threshold: Optional[int] = Field(
        None, 
        description="Minimum total engagement score (views + likes + comments) to filter videos. If not provided, tool fetches top engaged videos without filtering",
        ge=0
    )

    def run(self):
        """
        Search YouTube for highly engaged videos on the specified topic.
        Returns structured JSON data with video details and engagement metrics.
        """
        try:
            # Step 1: Validate inputs
            if not self.topic_or_keywords.strip():
                return json.dumps({
                    "error": "Topic or keywords cannot be empty",
                    "query": self.topic_or_keywords,
                    "total_results": 0,
                    "videos": []
                })
            
            # Step 2: Get API key from environment
            api_key = os.getenv("YOUTUBE_API_KEY")
            if not api_key:
                return json.dumps({
                    "error": "YouTube API key not found in environment variables. Please set YOUTUBE_API_KEY.",
                    "query": self.topic_or_keywords,
                    "total_results": 0,
                    "videos": []
                })
            
            # Step 3: Initialize YouTube API client
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # Step 4: Calculate date range (last week)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            
            # Step 5: Search for videos
            search_response = youtube.search().list(
                q=self.topic_or_keywords,
                part='id,snippet',
                maxResults=min(self.max_results * 2, 50),  # Get more results for filtering
                type='video',
                order='relevance',
                publishedAfter=start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                publishedBefore=end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                relevanceLanguage='en'
            ).execute()
            
            # Step 6: Extract video IDs
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if not video_ids:
                return json.dumps({
                    "query": self.topic_or_keywords,
                    "total_results": 0,
                    "search_metadata": {
                        "search_time": datetime.now(timezone.utc).isoformat(),
                        "time_range": "last_week",
                        "enhanced_query": self.topic_or_keywords,
                        "engagement_threshold": self.min_engagement_threshold,
                        "quota_used": 100  # search.list costs 100 units
                    },
                    "videos": []
                })
            
            # Step 7: Get detailed video information including statistics
            videos_response = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            # Step 8: Process videos and calculate engagement
            videos_data = []
            for video in videos_response.get('items', []):
                video_info = self._process_video(video)
                if video_info:
                    videos_data.append(video_info)
            
            # Step 9: Sort by engagement and apply threshold
            videos_data = self._sort_and_filter_videos(videos_data)
            
            # Step 10: Limit results
            videos_data = videos_data[:self.max_results]
            
            # Step 11: Calculate quota used
            quota_used = 100 + len(video_ids)  # search.list (100) + videos.list (1 per video)
            
            return json.dumps({
                "query": self.topic_or_keywords,
                "total_results": len(videos_data),
                "search_metadata": {
                    "search_time": datetime.now(timezone.utc).isoformat(),
                    "time_range": "last_week",
                    "enhanced_query": self.topic_or_keywords,
                    "engagement_threshold": self.min_engagement_threshold,
                    "quota_used": quota_used
                },
                "videos": videos_data
            })
            
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            return json.dumps({
                "error": f"YouTube API error: {error_details.get('error', {}).get('message', str(e))}",
                "query": self.topic_or_keywords,
                "total_results": 0,
                "videos": []
            })
        except Exception as e:
            return json.dumps({
                "error": f"Unexpected error: {str(e)}",
                "query": self.topic_or_keywords,
                "total_results": 0,
                "videos": []
            })

    def _process_video(self, video: Dict) -> Optional[Dict]:
        """
        Process a single video and extract relevant information.
        """
        try:
            snippet = video.get('snippet', {})
            statistics = video.get('statistics', {})
            content_details = video.get('contentDetails', {})
            
            # Extract basic information
            video_id = video.get('id')
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            channel_title = snippet.get('channelTitle', '')
            published_at = snippet.get('publishedAt', '')
            duration = content_details.get('duration', '')
            
            # Extract engagement metrics
            views = int(statistics.get('viewCount', 0))
            likes = int(statistics.get('likeCount', 0))
            comments = int(statistics.get('commentCount', 0))
            
            # Calculate total engagement (views + likes + comments)
            total_engagement = views + likes + comments
            
            # Get thumbnail URL
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = thumbnails.get('medium', {}).get('url', '') if 'medium' in thumbnails else thumbnails.get('default', {}).get('url', '')
            
            # Format duration for better readability
            formatted_duration = self._format_duration(duration)
            
            return {
                "id": video_id,
                "title": title,
                "description": description[:500] + "..." if len(description) > 500 else description,  # Truncate long descriptions
                "channel_title": channel_title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published_at": published_at,
                "duration": duration,
                "formatted_duration": formatted_duration,
                "thumbnail_url": thumbnail_url,
                "engagement_metrics": {
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "total_engagement": total_engagement
                }
            }
        except Exception as e:
            print(f"Error processing video: {e}")
            return None

    def _sort_and_filter_videos(self, videos: List[Dict]) -> List[Dict]:
        """
        Sort videos by engagement and apply minimum threshold filter.
        """
        # Filter by minimum engagement threshold if specified
        if self.min_engagement_threshold is not None:
            videos = [v for v in videos if v['engagement_metrics']['total_engagement'] >= self.min_engagement_threshold]
        
        # Sort by total engagement in descending order
        videos.sort(key=lambda x: x['engagement_metrics']['total_engagement'], reverse=True)
        
        return videos

    def _format_duration(self, duration: str) -> str:
        """
        Convert ISO 8601 duration to human-readable format.
        """
        try:
            if not duration:
                return "Unknown"
            
            # Parse ISO 8601 duration
            parsed_duration = isodate.parse_duration(duration)
            total_seconds = int(parsed_duration.total_seconds())
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        except Exception:
            return duration  # Return original if parsing fails

if __name__ == "__main__":
    # Test the tool
    tool = YouTubeSearchTool(
        topic_or_keywords="learning english",
        max_results=10,
        min_engagement_threshold=1000
    )
    print(tool.run()) 