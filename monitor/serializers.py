from rest_framework import serializers

from .models import Keyword, ContentItem, Flag


class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['created_at']


class ContentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentItem
        fields = ['id', 'title', 'source', 'body', 'last_updated', 'created_at']
        read_only_fields = ['created_at']


class FlagSerializer(serializers.ModelSerializer):
    keyword_name = serializers.CharField(source='keyword.name', read_only=True)
    content_title = serializers.CharField(source='content_item.title', read_only=True)
    content_source = serializers.CharField(source='content_item.source', read_only=True)

    class Meta:
        model = Flag
        fields = [
            'id',
            'keyword',
            'keyword_name',
            'content_item',
            'content_title',
            'content_source',
            'score',
            'status',
            'reviewed_at',
            'created_at',
        ]
        read_only_fields = [
            'keyword',
            'keyword_name',
            'content_item',
            'content_title',
            'content_source',
            'score',
            'reviewed_at',
            'created_at',
        ]


class FlagUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flag
        fields = ['status']

    def validate_status(self, value):
        if value not in ['pending', 'relevant', 'irrelevant']:
            raise serializers.ValidationError('Invalid status.')
        return value
