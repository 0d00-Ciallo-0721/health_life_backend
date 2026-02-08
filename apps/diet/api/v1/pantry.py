from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.diet.models import FridgeItem
from apps.diet.serializers.pantry import FridgeItemSerializer
from apps.diet.domains.pantry.services import PantryService

class FridgeItemListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FridgeItemSerializer
    
    def get_queryset(self):
        qs = FridgeItem.objects.filter(user=self.request.user).order_by('created_at') 
        search_query = self.request.query_params.get('search', '').strip()
        if search_query: qs = qs.filter(name__icontains=search_query)
        category = self.request.query_params.get('category', '').strip()
        if category and category != 'all': qs = qs.filter(category=category)
        return qs
        
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response({
                "code": 200, "msg": "success",
                "data": {"items": serializer.data, "total": self.paginator.page.paginator.count}
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "code": 200, "msg": "success",
            "data": {"items": serializer.data, "total": queryset.count()}
        })

class FridgeItemDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FridgeItemSerializer
    
    def get_queryset(self):
        return FridgeItem.objects.filter(user=self.request.user)

class FridgeSyncView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        op = request.data.get('operation', 'override')
        items = request.data.get('items', [])
        if not isinstance(items, list):
            return Response({"code": 400, "msg": "items必须是列表"}, status=400)
        
        count = PantryService.sync_fridge(request.user, op, items)
        return Response({"code": 200, "msg": f"成功同步 {count} 个食材"})