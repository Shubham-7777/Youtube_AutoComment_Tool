from django.db import models

# Create your models here.



class Comment(models.Model):
    video_id = models.CharField(max_length=255)
    comment_text = models.TextField()
    sentiment = models.CharField(max_length=10)
    reply_text = models.TextField(null=True, blank=True)  # Store the reply
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.comment_text} ({self.sentiment})"


"""
class Comment(models.Model):
    video_id = models.CharField(max_length=255)  # ID of the related video
    comment_text = models.TextField()             # The actual comment text
    sentiment = models.CharField(max_length=10)   # Sentiment: Positive, Negative, Neutral
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for when the comment 

    def __str__(self):
        return f"{self.comment_text} ({self.sentiment})"
"""