# HEAVYPOLY Hijacking Plan 🔥

**Status:** Phase 1 Complete ✅  
**Date:** November 5, 2025

## Overview

Style Engine is taking over HEAVYPOLY's hotkeys and pie menus to seamlessly integrate AI generation into the modeling workflow. This will make Style Engine feel like a native part of HEAVYPOLY rather than a separate addon.

---

## Phase 1: Foundation ✅ COMPLETE

**What We Did:**
- Added `enable_heavypoly_compatibility` toggle in addon preferences
- Created helper function `is_heavypoly_compatible()` in utils.py
- Set up UI in Advanced Settings with visual indicator (checkmark when enabled)

**Files Modified:**
- `prefs.py` - Added BoolProperty and UI toggle
- `utils.py` - Added compatibility check function

**How to Use:**
1. Go to Edit → Preferences → Add-ons → Style Engine
2. Expand addon settings
3. Expand "Advanced Settings"
4. Enable "Enable HEAVYPOLY Compatibility"

---

## Phase 2: Hotkey Hijacking 🎯 NEXT

**Goal:** Intercept HEAVYPOLY's frequently-used hotkeys and inject Style Engine functionality

**Target Hotkeys to Hijack:**

### Primary Targets (Most Useful)
- **Tab** - Add Style Engine to HEAVYPOLY's mode switch pie menu
- **Q** - HEAVYPOLY quick menu → Add AI generation option
- **Shift+A** - Add menu → Include AI texture/material generation
- **Alt+A** - Area pie menu → Add Style Engine viewport option
- **Shift+S** - Save pie menu → Add "Save AI Iteration" option

### Secondary Targets (Convenience)
- **Shift+X** - Special operations → Add AI shortcuts
- **Ctrl+Shift+Alt+C** - Clean operations → Add texture cleanup
- **Alt+Q** - Properties popup → Show AI settings

**Implementation Strategy:**
```python
# In __init__.py or new heavypoly_integration.py

def register_heavypoly_hijacks():
    if not is_heavypoly_compatible():
        return
    
    # Check if HEAVYPOLY is installed
    if 'HEAVYPOLY' not in bpy.context.preferences.addons:
        return
    
    # Inject into HEAVYPOLY's keymaps
    # Override specific pie menu items
    # Add Style Engine options to HEAVYPOLY menus
```

**Key Principles:**
- Only activate when compatibility mode is enabled
- Don't break HEAVYPOLY's existing functionality
- Make it feel seamless and natural
- Graceful fallback if HEAVYPOLY isn't installed

---

## Phase 3: Pie Menu Integration 🥧

**Goal:** Add Style Engine commands directly into HEAVYPOLY's pie menus

**Target Menus:**

### HEAVYPOLY_pie_specials (Shift+X)
Add:
- "Generate AI Texture" 
- "Apply AI to Selection"
- "Save Iteration"

### HEAVYPOLY_pie_view (Shift+~)
Add:
- "Toggle AI Vision Workspace"
- "Show AI Output"

### HEAVYPOLY_pie_add (Shift+A)
Add:
- "AI Material"
- "AI Texture from Image"

**Implementation:**
```python
# Inject into existing pie menus
def extend_heavypoly_pie_menu(menu_class):
    original_draw = menu_class.draw
    
    def new_draw(self, context):
        # Call original HEAVYPOLY draw
        original_draw(self, context)
        
        # Add Style Engine options
        if is_heavypoly_compatible():
            pie = self.layout.menu_pie()
            pie.operator("styleengine.generate_texture")
    
    menu_class.draw = new_draw
```

---

## Phase 4: Workflow Enhancements 🚀

**Goal:** Make Style Engine respond to HEAVYPOLY's workflow patterns

**Features:**

### Smart Context Detection
- When user selects object → Auto-show AI texture panel
- When user enters Edit Mode → Show vertex-based AI options
- When user saves → Auto-save AI iteration

### HeavyPoly Naming Conventions
- Respect HEAVYPOLY's object naming patterns
- Auto-detect HEAVYPOLY cameras (usually named "Camera.HP")
- Don't interfere with HEAVYPOLY's workspace switching

### Visual Integration
- Match HEAVYPOLY's UI style (if possible)
- Use compatible icons
- Position panels near HEAVYPOLY elements

---

## Phase 5: Power User Features 💪

**Goal:** Advanced features for users who use both addons heavily

**Features:**

### AI-Enhanced Modeling Shortcuts
- **Ctrl+Alt+G** - Generate AI texture from current viewport
- **Ctrl+Alt+I** - Apply IPAdapter style transfer
- **Ctrl+Alt+R** - Re-render with current prompt

### Macro Recording
- Record HEAVYPOLY modeling actions
- Auto-generate AI textures at key steps
- Save entire workflow as preset

### Quick Iteration
- Right-click on object → "AI Texture Variants"
- Generates 4 quick variations
- One-click apply

---

## Technical Architecture

### File Structure
```
styleengine/
├── __init__.py              # Main registration
├── prefs.py                 # Settings (✅ Phase 1 complete)
├── utils.py                 # Helpers (✅ Phase 1 complete)
├── ui_panel.py              # Main UI
├── heavypoly_hijack.py      # 🎯 NEW - Hotkey hijacking
├── heavypoly_integration.py # 🎯 NEW - Menu injection
└── workspace_setup.py       # Workspace management
```

### Key Classes to Create

#### `HeavyPolyKeymapHijacker`
- Scans HEAVYPOLY's keymaps
- Injects Style Engine operators
- Maintains original functionality

#### `HeavyPolyMenuExtender`
- Extends existing pie menus
- Adds Style Engine options
- Clean UI integration

#### `WorkflowBridge`
- Detects HEAVYPOLY workflow state
- Triggers appropriate Style Engine actions
- Context-aware suggestions

---

## Safety & Compatibility

### Safeguards
1. **Check before hijacking** - Always verify HEAVYPOLY is installed
2. **Graceful degradation** - Works fine if HEAVYPOLY isn't there
3. **Easy disable** - Toggle in preferences instantly reverts
4. **No data loss** - Never interfere with scene data
5. **Debug mode** - Verbose logging when enabled

### Testing Checklist
- [ ] Works with HEAVYPOLY enabled
- [ ] Works with HEAVYPOLY disabled
- [ ] Works when HEAVYPOLY is uninstalled
- [ ] Doesn't break HEAVYPOLY's existing hotkeys
- [ ] Clean uninstall/disable
- [ ] No console errors
- [ ] Performance impact minimal

---

## Next Immediate Steps

1. **Create `heavypoly_hijack.py`**
   - Implement keymap detection
   - Add hotkey override system
   
2. **Test compatibility detection**
   - Check if HEAVYPOLY is installed
   - Verify version compatibility
   
3. **Implement first hijack**
   - Start with simple menu addition
   - Test thoroughly before expanding

---

## Notes

- Keep UI panel clean (as requested)
- All HEAVYPOLY stuff is hidden unless compatibility mode enabled
- This is about enhancing workflow, not replacing HEAVYPOLY
- The goal is to make AI generation feel native to modeling workflow

---

**Ready to hijack HEAVYPOLY and make it ours! 🔥**

