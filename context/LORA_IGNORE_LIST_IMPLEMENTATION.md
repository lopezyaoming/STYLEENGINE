# LoRA Ignore List Implementation

**Date**: 2026-01-26  
**Feature**: Filter out unwanted LoRAs from dropdown using `loras/ignore.txt`

## Purpose

Prevent specific LoRAs from appearing in the addon's dropdown menu. Useful for:
- Hiding incompatible LoRAs (Flux models in SDXL workflows)
- Excluding broken/test models
- Filtering out old/deprecated versions
- Removing video/T2V LoRAs from image generation

## Implementation

### Files Modified

**`ui_panel.py`:**

1. **Added `_load_lora_ignore_list()` helper function** (before `get_lora_items()`)
   - Reads `loras/ignore.txt`
   - Parses one filename per line
   - Handles paths (extracts just filename from "LoRAs/subfolder/file.safetensors")
   - Skips empty lines and comments (`#`)
   - Returns a set for O(1) lookup performance

2. **Modified `get_lora_items()` function**
   - Calls `_load_lora_ignore_list()` to get ignored set
   - Filters out any LoRAs matching the ignore list
   - Counts and logs how many were filtered
   - Console output: `"✓ Found 42 LoRa models on server (8 filtered)"`

### Usage

**Format of `loras/ignore.txt`:**

```
# Comments start with #
# One filename per line

# Incompatible models
flux2_berthe_morisot.safetensors
qwen_image_union_diffsynth_lora.safetensors

# Old versions
LoRAs/Wan22-Lightning/old/Wan2.2-Lightning_T2V-v1.1-A14B-4steps-lora_LOW_fp16.safetensors

# Video LoRAs (not for image generation)
Wan2.2-Lightning_T2V-v1.1-A14B-4steps-lora_HIGH_fp16.safetensors
```

**Key Features:**
- ✅ Supports full paths (extracts filename automatically)
- ✅ Supports comments with `#`
- ✅ Case-sensitive matching
- ✅ No restart required (clears cache every 5 minutes)
- ✅ Graceful fallback if file doesn't exist

## Testing

1. **Add a LoRA to ignore list:**
   ```
   echo "test_lora.safetensors" >> loras/ignore.txt
   ```

2. **Refresh LoRA dropdown** in Blender UI (cache auto-clears in 5 min, or use Refresh button)

3. **Verify console output:**
   ```
   [Style Engine] Loaded 8 ignored LoRAs from ignore.txt
   [Style Engine] ✓ Found 42 LoRa models on server (8 filtered)
   ```

4. **Check dropdown:** Ignored LoRAs should not appear

## Performance

- **O(1) lookup** using Python set
- **Cached for 5 minutes** (ignore list is re-read on cache refresh)
- **No impact** on normal operation if file doesn't exist

## Future Enhancement (Not Implemented)

The `loras/keywords.txt` file exists but is not yet implemented. It will map LoRA filenames to trigger keywords:

```
chunky_sdxl_v1.safetensors: "chunky, rusty, DIY, diorama"
```

This would auto-suggest keywords when a LoRA is selected.
