from django.shortcuts import render

# Create your views here.
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from django.shortcuts import redirect
# comments/views.py
import os
import openai
from django.shortcuts import render, redirect
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .utils import credentials_to_dict
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import time
import random
from .models import Comment
# Home view
def home(request):
    return render(request, 'comments/home.html')

# Initiate OAuth flow

def home(request):
    """
    This function renders the home page of the web application.

    Parameters:
    request (HttpRequest): The request object containing information about the client's request.

    Returns:
    HttpResponse: The rendered home page as an HttpResponse object.
    """
    return render(request, 'comments/home.html')



def google_oauth(request):
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
        scopes=settings.GOOGLE_OAUTH2_SCOPES,
        redirect_uri=request.build_absolute_uri(reverse('oauth2callback'))
    )
    print(flow, "flow 51")
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    print(authorization_url, "authorization_url", state, "authorization_url, state 56")

    request.session['state'] = state
    return redirect(authorization_url)

"""
@csrf_exempt
def oauth2callback(request):
    print(request.build_absolute_uri(), "OAuth Callback URL")  # Log the callback URL
    state = request.session.get('state')
    print(state, "OAuth State")  # Log the state

    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
        scopes=settings.GOOGLE_OAUTH2_SCOPES,
        state=state,
        redirect_uri=request.build_absolute_uri(reverse('oauth2callback'))
    )

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        credentials = flow.credentials
        request.session['credentials'] = credentials_to_dict(credentials)
    except Exception as e:
        print(f"Error during token fetch: {e}")  # Log any error
        return redirect('error_page')  # Add an error page or message here

    return redirect('select_channel')
"""

# OAuth2 callback
@csrf_exempt
def oauth2callback(request):

    
    print(request, "request 66")
    state = request.session['state']
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
        scopes=settings.GOOGLE_OAUTH2_SCOPES,
        state=state,
        redirect_uri=request.build_absolute_uri(reverse('oauth2callback'))
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials
    request.session['credentials'] = credentials_to_dict(credentials)

    return redirect('select_channel')



# Select YouTube Channel
def select_channel(request):
    credentials_dict = request.session.get('credentials')
    if not credentials_dict:
        return redirect('home')

    credentials = Credentials(**credentials_dict)
    youtube = build('youtube', 'v3', credentials=credentials)

    channels_response = youtube.channels().list(
        mine=True,
        part='snippet,contentDetails,statistics'
    ).execute()

    channels = channels_response.get('items', [])
    
    return render(request, 'comments/select_channel.html', {'channels': channels})

# Select YouTube Video
def select_video(request):
    if request.method == 'POST':
        selected_channel_id = request.POST.get('channel_id')
        request.session['selected_channel_id'] = selected_channel_id

        credentials_dict = request.session.get('credentials')
        if not credentials_dict:
            return redirect('home')

        credentials = Credentials(**credentials_dict)
        youtube = build('youtube', 'v3', credentials=credentials)

        videos_response = youtube.search().list(
            channelId=selected_channel_id,
            part='snippet',
            maxResults=50,
            order='date',
            type='video'
        ).execute()

        videos = videos_response.get('items', [])
        #breakpoint()
        return render(request, 'comments/select_video.html', {'videos': videos})

    return redirect('select_channel')

# Gather Insights from User
def gather_insights(request):
    if request.method == 'POST':
        selected_video_id = request.POST.get('video_id')
        request.session['selected_video_id'] = selected_video_id

        return render(request, 'comments/gather_insights.html')

    return redirect('select_video')


def analyze_sentiment(comment_text):
    openai.api_key = os.getenv('OPENAI_API_KEY')

    prompt = f"Determine the type/sentiment/tone/mood of this YouTube comment: \"{comment_text}\". Respond with 'positive', 'neutral', or 'negative'. NOTE - IF not sure or unsure, respond with 'neutral' Its compulsory to have answer only out of this three."
    
    try:
        sentiment_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a sentiment analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10
        )
        sentiment = sentiment_response.choices[0].message['content'].strip().lower()
        #breakpoint()
        if sentiment not in ['positive', 'neutral', 'negative']:
            sentiment = 'neutral'
        return sentiment
    except Exception as e:
        print(f"Error during sentiment analysis: {e}")
        return 'neutral'  # Default to neutral if analysis fails


def process_comments(request):
    if request.method == 'POST':
        insights = request.POST.get('insights')
        video_id = request.session.get('selected_video_id')
        credentials_dict = request.session.get('credentials')

        if not video_id or not credentials_dict:
            return redirect('home')

        credentials = Credentials(**credentials_dict)
        youtube = build('youtube', 'v3', credentials=credentials)

        video_response = youtube.videos().list(
            id=video_id,
            part='snippet,statistics'
        ).execute()
        video_details = video_response.get('items', [])
        if video_details:
            video_title = video_details[0]['snippet']['title']
            print(f"Processing comments for video: {video_title}")

        # Fetch comments from YouTube
        response = youtube.commentThreads().list(
            videoId=video_id,
            part='snippet',
            maxResults=100,
            textFormat='plainText'
        ).execute()

        comments = response.get('items', [])

        # Iterate through comments and analyze sentiment
        for comment in comments:
            top_comment = comment['snippet']['topLevelComment']
            comment_id = top_comment['id']
            comment_text = top_comment['snippet']['textOriginal']

            # Check if we've already replied to this comment
            existing_comment = Comment.objects.filter(video_id=video_id, comment_text=comment_text).first()

            # Skip if we've already replied to this comment
            if existing_comment and existing_comment.reply_text:
                print(f"Already replied to comment: {comment_text}")
                continue

            # Analyze sentiment of the comment (positive, neutral, negative)
            sentiment = analyze_sentiment(comment_text)

            # Save the comment with its sentiment in the database if it's not already saved
            if not existing_comment:
                comment_record = Comment.objects.create(
                    video_id=video_id,
                    comment_text=comment_text,
                    sentiment=sentiment
                )
            else:
                comment_record = existing_comment

            # Only reply to positive or neutral comments
            if sentiment in ['positive', 'neutral']:

                # Generate unique reply using OpenAI
                openai.api_key = os.getenv('OPENAI_API_KEY')
                prompt = f"Respond to this YouTube comment in a {insights} tone:\n\nComment: {comment_text}\nReply:"

                try:
                    openai_response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=60,
                        temperature=0.7,
                        n=3  # Generate 3 variations to choose a unique one
                    )
                    reply_texts = [choice.message['content'].strip() for choice in openai_response.choices]

                    # Ensure uniqueness by picking a reply not already used for this video
                    unique_reply = None
                    for reply in reply_texts:
                        if not Comment.objects.filter(video_id=video_id, reply_text=reply).exists():
                            unique_reply = reply
                            break

                    if unique_reply:
                        # Save reply to the comment record
                        comment_record.reply_text = unique_reply
                        comment_record.save()

                        # Post the reply to YouTube
                        youtube.comments().insert(
                            part='snippet',
                            body={
                                'snippet': {
                                    'parentId': comment_id,
                                    'textOriginal': unique_reply
                                }
                            }
                        ).execute()
                        print(f"Replied to comment: {comment_text}")
                        #breakpoint()
                except Exception as e:
                    print(f"Error replying to comment {comment_id}: {e}")
                    continue  # Skip to the next comment in case of error

                # Randomize delay between replies (between 5 and 15 seconds)
                delay = random.randint(0, 120)
                print(f"Waiting for {delay} seconds before replying to the next comment...")
                time.sleep(delay)

        return redirect('success')

    return redirect('gather_insights')


"""
# Process Comments and Generate Replies
def process_comments(request):
    if request.method == 'POST':
        insights = request.POST.get('insights')
        video_id = request.session.get('selected_video_id')
        credentials_dict = request.session.get('credentials')

        if not video_id or not credentials_dict:
            return redirect('home')

        credentials = Credentials(**credentials_dict)
        youtube = build('youtube', 'v3', credentials=credentials)

        video_response = youtube.videos().list(
            id=video_id,
            part='snippet,statistics'
        ).execute()
        video_details = video_response.get('items', [])
        if video_details:
            video_title = video_details[0]['snippet']['title']
            print(f"Processing comments for video: {video_title}")


        # Fetch comments
        comments = []
        response = youtube.commentThreads().list(
            videoId=video_id,
            part='snippet',
            maxResults=100,
            textFormat='plainText'
        ).execute()

        comments.extend(response.get('items', []))

        # Iterate through comments and reply using OpenAI
        for comment in comments:
            print(comment, "comment 164")
            top_comment = comment['snippet']['topLevelComment']
            comment_id = top_comment['id']
            comment_text = top_comment['snippet']['textOriginal']

            # Generate reply using OpenAI
            #openai.api_key = OPENAI_API_KEY  # Ensure you set this environment variable
            openai.api_key = os.getenv('OPENAI_API_KEY')  # Ensure you set this environment variable

            prompt = f"Respond to this YouTube comment in a {insights} tone:\n\nComment: {comment_text}\nReply:"
            try:
                openai_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    #prompt=prompt,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=60,
                    temperature=0.7
                )
                reply_text = openai_response.choices[0].message['content'].strip()

                # Post reply to the comment
                youtube.comments().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'parentId': comment_id,
                            'textOriginal': reply_text
                        }
                    }
                ).execute()
            except Exception as e:
                print(f"Error replying to comment {comment_id}: {e}")
                continue  # Skip to the next comment in case of error

        return redirect('success')

    return redirect('gather_insights')

"""# Success Page
def success(request):
    return render(request, 'comments/success.html')



def view_negative_comments(request):
    video_id = request.session.get('selected_video_id')
    credentials_dict = request.session.get('credentials')

    if not video_id or not credentials_dict:
        return redirect('home')

    credentials = Credentials(**credentials_dict)
    youtube = build('youtube', 'v3', credentials=credentials)

    # Fetch comments
    response = youtube.commentThreads().list(
        videoId=video_id,
        part='snippet',
        maxResults=100,
        textFormat='plainText'
    ).execute()

    comments = response.get('items', [])
    negative_comments = []
    positive_comments = []
    negative_comments = []

    # Iterate through comments and analyze sentiment
    for comment in comments:
        top_comment = comment['snippet']['topLevelComment']
        comment_text = top_comment['snippet']['textOriginal']

        # Analyze sentiment of the comment
        sentiment = analyze_sentiment(comment_text)

        if sentiment == 'negative':
            # Store negative comments for display
            negative_comments.append(comment_text)

    return render(request, 'comments/view_negative_comments.html', {'negative_comments': negative_comments})
