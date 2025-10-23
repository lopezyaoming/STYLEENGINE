# Blender UI Features

## Background Opacity Control

### Location
**Blender → Style Engine Panel → Workspace Setup**

### Purpose
Quickly toggle between viewing your 3D geometry and the AI-generated image by adjusting the background transparency.

### How to Use

1. Open the Style Engine panel (press `N` in 3D viewport)
2. Expand **"Workspace Setup"** section
3. Find **"Background Opacity"** slider
4. Adjust the slider:
   - **0.0** = Fully transparent (see only geometry)
   - **0.5** = 50% blend (see both geometry and AI)
   - **1.0** = Fully opaque (see only AI image)

### Use Cases

#### Geometry Check
```
Background Opacity: 0.0
```
- See your 3D models clearly
- Check positioning, scale, proportions
- Verify modeling is correct

#### Alignment Check
```
Background Opacity: 0.5
```
- Overlay AI image on geometry
- Check if AI interpretation matches your intent
- Verify composition alignment

#### AI Preview
```
Background Opacity: 1.0
```
- See full AI-generated result
- Check final visual quality
- Compare different prompts/settings

### Workflow Examples

#### Modeling Session
```
1. Set opacity to 0.0 while modeling
2. Enable "Refresh Viewport" + "Auto-Generate AI"
3. After each change, set opacity to 1.0
4. Check AI result
5. Set opacity back to 0.0
6. Continue modeling
```

#### Composition Refinement
```
1. Set opacity to 0.5
2. Move camera to match AI composition
3. Adjust object positions
4. Watch AI update in real-time
5. Fine-tune until perfect alignment
```

#### Rapid Iteration
```
1. Keep opacity at 1.0
2. Change prompt in UI
3. Wait for AI update
4. If not matching, set to 0.0
5. Adjust geometry
6. Set back to 1.0
7. Repeat
```

### Keyboard Shortcut Tip

**Want faster access?** Consider creating a Blender keymap:
1. Edit → Preferences → Keymap
2. 3D View → 3D View (Global)
3. Add New → wm.context_set_float
4. Set data path: `scene.style_engine_props.background_opacity`
5. Assign key (e.g., `Shift+Alt+O`)

### Technical Details

- **Property Type**: Float (0.0 to 1.0)
- **Default Value**: 1.0 (fully opaque)
- **Updates**: Real-time (no render needed)
- **Applies To**: AI camera background image only
- **Stored In**: Scene properties (per-scene setting)

### Pro Tips

1. **Quick Toggle**: 
   - Bookmark opacity 0.0 and 1.0 for instant switching
   - Use 0.5 as your "comparison mode"

2. **Layer Visualization**:
   - Use with Blender's X-ray mode for even more control
   - Combine with viewport overlays

3. **Reference Workflow**:
   - Set opacity to 0.3
   - Use AI image as a visual reference
   - Model directly over it

4. **Animation**:
   - Keyframe the opacity property
   - Create smooth transitions in renders
   - (Advanced: export as video with blended views)

### Comparison: Before vs After

**Before (No Opacity Control)**:
- Had to manually hide/show geometry
- Switch between viewports
- Time-consuming comparison

**After (With Opacity Slider)**:
- Instant visual switching
- Smooth blending for comparison
- One-slider workflow

---

## Related Features

### Refresh Viewport
Controls whether the AI image auto-refreshes.

**When to use each:**
- `Refresh Viewport OFF` + `Opacity 0.0` = Pure modeling mode
- `Refresh Viewport ON` + `Opacity 1.0` = Live AI preview
- `Refresh Viewport ON` + `Opacity 0.5` = Live comparison

### Auto-Generate AI
Controls whether new workflows are sent automatically.

**Typical workflow:**
1. Model with `Auto-Generate OFF`, `Opacity 0.0`
2. When ready to test, enable `Auto-Generate`
3. Adjust `Opacity` to compare
4. Iterate

---

## FAQ

### Q: Does changing opacity trigger a new render?
**A:** No, it's instant. Only affects display.

### Q: Does opacity affect the AI generation?
**A:** No, AI always uses full geometry. Opacity is display-only.

### Q: Can I have different opacity per scene?
**A:** Yes, it's stored per-scene.

### Q: What if I want to save an opacity preset?
**A:** Currently manual, but you can script it with Python:
```python
bpy.context.scene.style_engine_props.background_opacity = 0.5
```

### Q: Does this work with multiple cameras?
**A:** It only affects the `ai_camera` background image.

---

## Visual Examples

### Opacity 0.0 (Geometry Only)
```
┌─────────────────────┐
│                     │
│   [3D Geometry]     │
│   Pure wireframe    │
│   or solid view     │
│                     │
└─────────────────────┘
```

### Opacity 0.5 (Blended)
```
┌─────────────────────┐
│                     │
│   [AI Image]        │
│        +            │
│   [Geometry]        │
│   = Overlay         │
│                     │
└─────────────────────┘
```

### Opacity 1.0 (AI Only)
```
┌─────────────────────┐
│                     │
│   [AI Generated]    │
│   Full render       │
│   No geometry       │
│                     │
└─────────────────────┘
```

---

## Integration with Other Tools

### Compositor
- Background opacity doesn't affect compositor
- Compositor sees full renders

### Render Output
- Render output is always full opacity
- Opacity is viewport-only

### Screenshots
- Screenshots capture current opacity
- Good for documentation/comparison

---

## Shortcuts & Efficiency

### Recommended Opacity Values

| Opacity | Purpose | When to Use |
|---------|---------|-------------|
| **0.0** | Pure geometry | Modeling, UV unwrap, rigging |
| **0.3** | Light reference | Modeling with AI as guide |
| **0.5** | Comparison | Check alignment, composition |
| **0.7** | AI-dominant | Final checks with geometry hints |
| **1.0** | Pure AI | Final preview, prompt testing |

### Workflow Presets

**Preset 1: Pure Modeling**
- Background Opacity: 0.0
- Refresh Viewport: OFF
- Auto-Generate: OFF

**Preset 2: Live Preview**
- Background Opacity: 1.0
- Refresh Viewport: ON
- Auto-Generate: ON

**Preset 3: Comparison Mode**
- Background Opacity: 0.5
- Refresh Viewport: ON
- Auto-Generate: ON

**Preset 4: Reference Mode**
- Background Opacity: 0.3
- Refresh Viewport: OFF
- Auto-Generate: OFF

---

## Future Enhancements

Planned features:
- [ ] Preset buttons (0%, 50%, 100%)
- [ ] Keyboard shortcuts built-in
- [ ] Opacity animation for viewport
- [ ] Per-viewport opacity (different in each window)
- [ ] Opacity presets saved with scene

---

Enjoy the new visual control! 🎨✨

