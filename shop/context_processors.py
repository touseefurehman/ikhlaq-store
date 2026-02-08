from .models import Category, Cart

def cart_context(request):
    """
    Context processor to add cart count and categories to all templates
    """
    cart_count = 0
    categories = []
    
    try:
        # Get categories
        categories = Category.objects.all()
        
        # Get cart count
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first()
        
        if cart:
            cart_count = cart.items.count()
            
    except Exception as e:
        # Log error but don't crash the site
        print(f"Context processor error: {e}")
        # Return default values
        categories = []
        cart_count = 0
    
    return {
        'cart_count': cart_count,
        'categories': categories
    }