from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Keyword, Flag
from .serializers import KeywordSerializer, FlagSerializer, FlagUpdateSerializer
from .services.scanner import run_scan


@api_view(['POST'])
def create_keyword(request):
    """POST /keywords/ - Add a new keyword to monitor."""
    serializer = KeywordSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def list_keywords(request):
    """GET /keywords/ - List all keywords."""
    keywords = Keyword.objects.all().order_by('-created_at')
    serializer = KeywordSerializer(keywords, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def trigger_scan(request):
    """POST /scan/ - Trigger a scan against all content sources."""
    result = run_scan()
    if "error" in result:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
def list_flags(request):
    """
    GET /flags/ - List all flags.
    Optional query params:
      ?status=pending|relevant|irrelevant
      ?keyword=<keyword_name>
    """
    flags = Flag.objects.select_related('keyword', 'content_item').all()

    status_filter = request.query_params.get('status')
    if status_filter:
        flags = flags.filter(status=status_filter)

    keyword_filter = request.query_params.get('keyword')
    if keyword_filter:
        flags = flags.filter(keyword__name__icontains=keyword_filter)

    flags = flags.order_by('-score', '-created_at')
    serializer = FlagSerializer(flags, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
def update_flag(request, pk):
    """PATCH /flags/<id>/ - Update review status of a flag."""
    try:
        flag = Flag.objects.get(pk=pk)
    except Flag.DoesNotExist:
        return Response({"error": "Flag not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = FlagUpdateSerializer(flag, data=request.data, partial=True)
    if serializer.is_valid():
        new_status = serializer.validated_data.get('status')

        if new_status == 'irrelevant':
            flag.suppressed_until_update = flag.content_item.last_updated
            flag.reviewed_at = timezone.now()
        elif new_status in ['relevant', 'pending']:
            flag.suppressed_until_update = None
            flag.reviewed_at = timezone.now()

        flag.status = new_status
        flag.save()

        return Response(FlagSerializer(flag).data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
