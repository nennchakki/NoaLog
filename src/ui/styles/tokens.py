"""
NoaLog Design Tokens - Noa Theme
生塩ノア（ミレニアム×セミナー書記）モチーフ

キーワード: 清潔、理性的、書記、監査、整然、透明感
"""

# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    # Backgrounds
    "bg_light": "#F6F1E6",       # アイボリー（メイン背景）
    "bg_dark": "#0B1B2B",        # 濃紺（ヘッダー）
    "bg_panel": "#FFFFFF",       # 白（カード/パネル）
    "bg_hover": "#F0F7FF",       # 薄い水色（ホバー）
    "bg_selected": "#E5F4FF",    # 選択背景
    "bg_input": "#FAFAFA",       # 入力フィールド背景

    # Text
    "text_primary": "#121826",   # 本文
    "text_secondary": "#5A6578", # 副次テキスト
    "text_tertiary": "#8A95A8",  # タイムスタンプ等
    "text_on_dark": "#EAF2FF",   # 濃紺背景上
    "text_on_accent": "#FFFFFF", # アクセント背景上

    # Accent (Noa Cyan)
    "accent": "#63C6FF",         # メインアクセント
    "accent_light": "#A7E4FF",   # 薄いアクセント
    "accent_dark": "#3BA8E8",    # 濃いアクセント（ホバー）
    "accent_bg": "#E5F4FF",      # アクセント背景

    # Lines & Borders
    "line": "#C8D2E0",           # 区切り線
    "line_light": "#E5EAF2",     # 薄い線
    "border_focus": "#63C6FF",   # フォーカスリング

    # Semantic
    "success": "#4CAF50",        # 成功（控えめ緑）
    "warning": "#F5A623",        # 警告（黄）
    "error": "#E53935",          # エラー（赤）
    "narration": "#8A95A8",      # 地の文バッジ

    # Special - Halo
    "halo_idle": "#C8D2E0",      # ヘイロー待機
    "halo_active": "#63C6FF",    # ヘイロー動作中
    "halo_success": "#63C6FF",   # ヘイロー成功
    "halo_failed": "#8A95A8",    # ヘイロー失敗
    "halo_debounce": "#E5EAF2",  # ヘイローデバウンス

    # Badge
    "badge_edited": "#63C6FF",   # 編集済バッジ
    "badge_narration": "#C8D2E0", # 地の文バッジ
    "badge_low_conf": "#F5A623", # 低信頼バッジ（控えめ黄）
}

# =============================================================================
# TYPOGRAPHY
# =============================================================================

TYPOGRAPHY = {
    # Font Family
    "font_family": '"Hiragino Sans", "Noto Sans JP", "Yu Gothic UI", "Segoe UI", sans-serif',
    "font_family_mono": '"SF Mono", "Consolas", "Noto Sans Mono CJK JP", monospace',

    # Font Sizes
    "text_xs": "11px",    # タイムスタンプ、バッジ
    "text_sm": "12px",    # 副次情報
    "text_base": "14px",  # 本文（デフォルト）
    "text_lg": "16px",    # カードタイトル
    "text_xl": "18px",    # セクションタイトル
    "text_2xl": "24px",   # ヘッダータイトル

    # Font Weights
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_semibold": "600",
    "weight_bold": "700",

    # Line Heights
    "leading_tight": "1.25",
    "leading_normal": "1.5",
    "leading_relaxed": "1.75",
}

# =============================================================================
# SPACING
# =============================================================================

SPACING = {
    "space_0": "0px",
    "space_1": "4px",
    "space_2": "8px",
    "space_3": "12px",
    "space_4": "16px",
    "space_5": "20px",
    "space_6": "24px",
    "space_8": "32px",
    "space_10": "40px",
    "space_12": "48px",
}

# =============================================================================
# SHAPES
# =============================================================================

SHAPES = {
    # Border Radius
    "radius_sm": "6px",
    "radius_md": "10px",
    "radius_lg": "14px",
    "radius_xl": "20px",
    "radius_full": "9999px",  # 完全な円

    # Border Width
    "border_thin": "1px",
    "border_normal": "2px",
    "border_thick": "3px",

    # Shadows (控えめ)
    "shadow_sm": "0 1px 3px rgba(0, 0, 0, 0.06)",
    "shadow_md": "0 2px 8px rgba(0, 0, 0, 0.08)",
    "shadow_lg": "0 4px 16px rgba(0, 0, 0, 0.10)",

    # Focus Ring (ヘイロー意匠)
    "focus_ring": "0 0 0 3px rgba(99, 198, 255, 0.4)",
}

# =============================================================================
# ANIMATION
# =============================================================================

ANIMATION = {
    # Duration
    "duration_fast": 150,    # ms
    "duration_normal": 250,  # ms
    "duration_slow": 400,    # ms

    # Halo Animation
    "halo_rotation_duration": 2000,  # ms - 記録中の回転
    "halo_pulse_duration": 600,      # ms - 成功時のパルス
}

# =============================================================================
# LAYOUT
# =============================================================================

LAYOUT = {
    # Pane widths
    "left_pane_width": 240,
    "left_pane_min": 200,
    "left_pane_max": 300,

    "center_pane_min": 400,

    "right_pane_width": 360,
    "right_pane_min": 320,
    "right_pane_max": 450,

    # Header
    "header_height": 56,

    # Card
    "card_min_height": 72,
    "card_max_height": 120,

    # Halo
    "halo_size": 48,
}


def get_color(name: str) -> str:
    """Get color by name."""
    return COLORS.get(name, "#000000")


def get_spacing(name: str) -> str:
    """Get spacing by name."""
    return SPACING.get(name, "0px")


def get_spacing_int(name: str) -> int:
    """Get spacing as integer (without px)."""
    value = SPACING.get(name, "0px")
    return int(value.replace("px", ""))
