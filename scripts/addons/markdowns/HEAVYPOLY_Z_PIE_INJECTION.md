# HeavyPoly Z Pie Menu Injection 🪂

**Status:** ✅ IMPLEMENTED  
**Date:** 2025-11-05  
**Type:** Paratrooper-style injection (zero HeavyPoly modifications)

---

## What It Does

Injects Style Engine's AI rendering functionality into **HeavyPoly's Z key pie menu** (View/Shading pie).

When you press **Z** with HeavyPoly and Style Engine both active:
- You get HeavyPoly's normal shading options (Solid, Material Preview, Rendered, etc.)
- **PLUS** Style Engine's AI operations on the RIGHT side of the pie

---

## The "Paratrooper" Approach 🎯

This is a **self-contained injection** that:
- ✅ Requires **zero modifications** to HeavyPoly's code
- ✅ Only activates when `enable_heavypoly_compatibility` is ON
- ✅ Cleanly removes itself when disabled or addon unregisters
- ✅ Uses Blender's dynamic menu system (`append()` method)
- ✅ No conflicts, no permanent changes, no footprint

It's like **dropping paratroopers behind enemy lines** — they do their job and leave no trace when extracted!

---

## How It Works

### 1. Dynamic Menu Extension

HeavyPoly's Z pie menu is defined in `HP_MT_pie_shading`. When Style Engine registers in HeavyPoly compatibility mode:

```python
# From heavypoly_integration.py
if hasattr(bpy.types, 'HP_MT_pie_shading'):
    bpy.types.HP_MT_pie_shading.append(inject_into_heavypoly_shading)
```

This **appends our draw function** to HeavyPoly's menu class. When the menu is drawn, both HeavyPoly's items **and** our items appear.

### 2. Menu Injection Point

Our `inject_into_heavypoly_shading()` function runs **after** HeavyPoly's draw code, adding:

```python
def inject_into_heavypoly_shading(self, context):
    layout = self.layout
    split = layout.split()
    col = split.column(align=True)
    
    # Add our AI operators to the RIGHT side
    col.operator("style_engine.render_ai_passes_quick", ...)
    col.operator("style_engine.generate_ai_quick", ...)
    col.operator("style_engine.setup_workspace", ...)
```

### 3. Clean Unregister

When the addon is disabled or unloaded:

```python
def unregister():
    for menu_name, handler in _draw_handlers:
        menu_class = getattr(bpy.types, menu_name)
        menu_class.remove(handler)  # Clean removal, no trace left
```

---

## Added Operators

Three new **quick-access operators** are added:

### 1. `SE_OT_render_ai_passes_quick`
**Hotkey/Menu:** "🎨 Render AI"  
**What it does:** Renders combined pass from the current view using ultra-fast Workbench engine.  
**Use case:** Quick render without switching to AI workspace.

### 2. `SE_OT_generate_ai_quick`
**Hotkey/Menu:** "🎨 Generate"  
**What it does:** Renders combined pass (Workbench) + triggers AI generation in one click.  
**Use case:** Full AI workflow from any workspace.

### 3. `style_engine.setup_workspace`
**Hotkey/Menu:** "Setup AI"  
**What it does:** Sets up the AI Vision workspace (or hijacks HeavyPoly's "Modeling" workspace if in compatibility mode).  
**Use case:** Quick access to full AI environment.

---

## File Structure

```
styleengine/
├── heavypoly_integration.py    ← NEW! Paratrooper injection module
├── __init__.py                 ← Modified: imports and registers heavypoly_integration
├── prefs.py                    ← Contains enable_heavypoly_compatibility toggle
├── workspace_setup.py          ← Contains render_passes_for_ai() function
└── ...
```

---

## User Experience

### Without HeavyPoly Compatibility

Press **Z** → Standard Blender shading menu  
Style Engine works normally in its own workspace.

### With HeavyPoly Compatibility ENABLED

1. Enable in addon preferences: **"Enable HEAVYPOLY Compatibility"**
2. Reload addons or restart Blender
3. Press **Z** anywhere → You now see:
   - **LEFT/TOP/BOTTOM:** HeavyPoly's shading options
   - **RIGHT:** Style Engine's AI operations

**Zero setup, zero configuration, zero conflicts!**

---

## Technical Details

### Registration Flow

```
Style Engine loads
    ↓
heavypoly_integration.register() called
    ↓
Check: is_heavypoly_compatible()?
    ↓ YES
Register quick operators
    ↓
Check: Does bpy.types.HP_MT_pie_shading exist?
    ↓ YES
Append inject_into_heavypoly_shading to menu
    ↓
Store reference in _draw_handlers for clean unregister
    ↓
✅ Injection complete!
```

### Unregistration Flow

```
Style Engine unloads
    ↓
heavypoly_integration.unregister() called
    ↓
For each stored draw handler:
    menu_class.remove(handler)
    ↓
Unregister quick operators
    ↓
✅ Clean extraction, zero trace!
```

### Error Handling

- **HeavyPoly not installed:** Injection silently skips, no errors
- **Compatibility mode OFF:** Module doesn't register, no overhead
- **HeavyPoly removed mid-session:** Unregister handles gracefully

---

## Testing Checklist

- [ ] Install HeavyPoly addon
- [ ] Install Style Engine addon
- [ ] Enable "Enable HEAVYPOLY Compatibility" in Style Engine preferences
- [ ] Reload addons (`F3` → "Reload Scripts" or restart Blender)
- [ ] Press `Z` in 3D viewport
- [ ] Verify RIGHT side shows "🎨 Render AI", "🎨 Generate", "Setup AI"
- [ ] Click "🎨 Generate" → Should render passes and start AI generation
- [ ] Disable "Enable HEAVYPOLY Compatibility" in preferences
- [ ] Reload addons
- [ ] Press `Z` → Should show normal HeavyPoly menu (no Style Engine items)

---

## Why This Approach?

### Alternative 1: Modify HeavyPoly's Code ❌
**Problem:** Requires users to edit HeavyPoly files, breaks on updates, hard to maintain.

### Alternative 2: Replace Z Keymap ❌
**Problem:** Conflicts with HeavyPoly, user loses HeavyPoly's shading pie.

### Alternative 3: Use Different Hotkey ❌
**Problem:** User has to learn new hotkeys, doesn't integrate with HeavyPoly workflow.

### Our Approach: Dynamic Menu Extension ✅
**Benefit:** No code changes, no conflicts, seamless integration, clean uninstall.

---

## Future Extensions

This paratrooper pattern can be extended to other HeavyPoly pies:

- **X key:** Selection pie (could add "Select AI Objects")
- **Q key:** View pie (could add "Jump to AI Workspace")
- **W key:** Transform pie (could add "Apply AI Texture")
- **E key:** Modeling pie (could add "Generate Variations")

**Each injection is independent and self-contained!**

---

## Credits

- **HeavyPoly:** Original addon by Ian Hubert
- **Style Engine:** Spiri Bros Co
- **Integration pattern:** "Paratrooper" self-contained injection

---

## License

Style Engine is proprietary software by Spiri Bros Co.  
HeavyPoly is open source under its own license.  
This integration respects both licenses through non-invasive dynamic extension.

---

**TLDR:** Press Z, get HeavyPoly + Style Engine AI in one menu. Zero modifications required. 🪂🎨

