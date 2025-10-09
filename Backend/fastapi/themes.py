# Theme configurations based on your color palettes
THEMES = {
    "purple_gradient": {
        "name": "Purple Gradient",
        "colors": {
            "primary": "#A855F7",
            "secondary": "#7C3AED", 
            "accent": "#C084FC",
            "background": "#F8FAFC",
            "card": "#FFFFFF",
            "text": "#1E293B",
            "text_secondary": "#64748B"
        },
        "css_classes": "theme-purple-gradient"
    },
    "blue_navy": {
        "name": "Navy Blue",
        "colors": {
            "primary": "#1E40AF",
            "secondary": "#1E3A8A",
            "accent": "#3B82F6",
            "background": "#F1F5F9",
            "card": "#FFFFFF",
            "text": "#1E293B",
            "text_secondary": "#475569"
        },
        "css_classes": "theme-blue-navy"
    },
    "sunset_warm": {
        "name": "Sunset Warm",
        "colors": {
            "primary": "#F59E0B",
            "secondary": "#DC2626",
            "accent": "#EC4899",
            "background": "#FFFBEB",
            "card": "#FFFFFF",
            "text": "#1F2937",
            "text_secondary": "#6B7280"
        },
        "css_classes": "theme-sunset-warm"
    },
    "ocean_mint": {
        "name": "Ocean Mint",
        "colors": {
            "primary": "#10B981",
            "secondary": "#059669",
            "accent": "#06B6D4",
            "background": "#F0FDF4",
            "card": "#FFFFFF",
            "text": "#1F2937",
            "text_secondary": "#4B5563"
        },
        "css_classes": "theme-ocean-mint"
    },
    "dark_professional": {
        "name": "Dark Professional",
        "colors": {
            "primary": "#06B6D4",
            "secondary": "#0891B2",
            "accent": "#22D3EE",
            "background": "#0F172A",
            "card": "#1E293B",
            "text": "#F8FAFC",
            "text_secondary": "#CBD5E1"
        },
        "css_classes": "theme-dark-professional"
    }
}

def get_theme(theme_name: str = "purple_gradient"):
    return THEMES.get(theme_name, THEMES["purple_gradient"])

def get_all_themes():
    return THEMES
