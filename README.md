# Style Engine

> **AI-Powered Real-Time Visualization for Blender**

An in-house Blender addon that provides real-time AI-generated stylization of your 3D scenes as you model. Built for Blender 4.2+ by Spiri Bros Co.

![Version](https://img.shields.io/badge/version-0.3.3-blue)
![Blender](https://img.shields.io/badge/blender-4.2+-orange)
![Status](https://img.shields.io/badge/status-mvp--skeleton-yellow)

## 🎯 Vision

Style Engine creates a dual-viewport workflow where you can:
- **Model** in a traditional 3D workspace (left viewport)
- **Visualize** AI-stylized versions in real-time (right viewport)

Think of it as an "AI filter" that shows you how your scene looks when processed through AI models, updating automatically as you work.

## ✨ Current Status (MVP)

### ✅ Implemented
- **One-Click Workspace Setup**: Automatic dual-viewport configuration
- **AI Camera System**: Smart camera positioning and background overlay
- **API Credentials Management**: Secure storage with environment variable support
- **Directory Management**: Auto-creation of temp folders and placeholder images
- **Complete UI Panel**: All controls and settings ready
- **LoRa Model Selection**: Dynamic discovery from ComfyUI server with adjustable strength
- **UV Texture Generation**: AI-powered texture generation for existing meshes (Hunyuan 3D 2.1)
- **Comprehensive Documentation**: Full guides for users and developers

### ⏳ Coming Next
- Auto-refresh timer system
- Viewport rendering and capture
- RunComfy API integration
- Real-time AI image generation
- Configurable update intervals

## 🚀 Quick Start

### Installation

```bash
# Run as Administrator (Windows)
setup_dev_addon.bat
```

Or manually:
1. Copy `scripts/addons/styleengine` to your Blender addons folder
2. Enable "Style Engine" in Blender Preferences → Add-ons

### Usage

1. **Open Blender** and enable the addon
2. **Press N** in 3D Viewport → Style Engine tab
3. **Position your view** where you want
4. **Click "Setup Workspace"**

That's it! You now have a split workspace ready for AI visualization.

## 📚 Documentation

### For Users
- **[Quick Start Guide](QUICKSTART.md)** - Get running in 3 minutes
- **[MVP Overview](MVP_AI_VISION.md)** - Complete feature documentation
- **[Testing Checklist](TESTING_CHECKLIST.md)** - Verify everything works
- **[API Setup Guide](API_SETUP_GUIDE.md)** - Configure RunComfy credentials

### For Developers
- **[Architecture Overview](ARCHITECTURE.md)** - System design and data flow
- **[Code Documentation](scripts/addons/styleengine/README.md)** - API reference
- **[MVP Summary](MVP_SUMMARY.md)** - Implementation details

## 🎨 Features

### Workspace Management
- Automatic "AI" workspace creation
- Split-screen layout (modeling + visualization)
- Camera-locked AI viewport
- Seamless workspace switching

### Camera System
- Auto-positioning at current view (Ctrl+Alt+0 behavior)
- Background image overlay (100% opacity)
- Display in front of geometry
- Automatic stretch-to-fit

### API Integration (Ready)
- RunComfy API credentials
- Environment variable support
- Secure password fields
- Test connection functionality

### UI Controls
- Library ID management
- Scene descriptions and keywords
- Per-object keyword support
- Depth influence slider
- Silhouette control
- Expandable sections

## 🛠️ Tech Stack

- **Blender**: 4.2+
- **Python**: 3.x (Blender bundled)
- **AI Service**: RunComfy (ready for integration)
- **File Format**: PNG for AI outputs

## 📦 Project Structure

```
STYLEENGINE/
├── README.md                    # This file
├── QUICKSTART.md               # Quick installation guide
├── MVP_AI_VISION.md            # MVP documentation
├── MVP_SUMMARY.md              # Implementation summary
├── ARCHITECTURE.md             # System architecture
├── TESTING_CHECKLIST.md        # Testing procedures
├── API_SETUP_GUIDE.md          # API configuration
├── LICENSE                     # License file
├── context/
│   └── context.txt            # Project vision
└── scripts/
    └── addons/
        └── styleengine/
            ├── __init__.py            # Main addon file
            ├── blender_manifest.toml  # Blender 4.2+ manifest
            ├── prefs.py              # Preferences panel
            ├── ui_panel.py           # Main UI
            ├── utils.py              # Helper functions
            ├── workspace_setup.py    # MVP core functionality
            └── README.md             # Code documentation
```

## 🧪 Testing

Run through the complete test suite:

```bash
# See TESTING_CHECKLIST.md for full procedures
```

Quick test:
1. Click "Setup Workspace"
2. Verify two viewports appear
3. Check `ai_camera` exists in outliner
4. Confirm `temp/ai_vision/current_ai.png` created

## 🔧 Development

### Prerequisites
- Blender 4.2 or higher
- Python 3.x (included with Blender)
- Windows 10+ (tested), Mac/Linux (should work)

### Development Setup

```bash
# Use symbolic link for live development
setup_dev_addon.bat
```

### Making Changes

1. Edit files in `scripts/addons/styleengine/`
2. In Blender: F3 → "Reload Scripts"
3. Test your changes
4. Repeat

See [Developer Documentation](scripts/addons/styleengine/README.md) for API reference.

## 🎯 Roadmap

### Phase 1: MVP Skeleton ✅ (Current)
- [x] Workspace setup system
- [x] Camera and background image
- [x] UI panel and controls
- [x] API credentials management
- [x] Documentation

### Phase 2: Auto-Refresh (Next)
- [ ] Timer-based rendering
- [ ] Viewport capture system
- [ ] Image reload automation
- [ ] User-configurable intervals

### Phase 3: AI Integration
- [ ] RunComfy API connection
- [ ] Image upload and processing
- [ ] Prompt generation from scene data
- [ ] Real-time updates

### Phase 4: Advanced Features
- [ ] Multiple AI models
- [ ] History/timeline
- [ ] Animation support
- [ ] Batch processing
- [ ] Export capabilities

## 🤝 Contributing

This is an in-house project for Spiri Bros Co. For questions or suggestions, reach out to the team.

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🙏 Credits

**Developed by**: Spiri Bros Co  
**Built for**: Blender 4.2+  
**AI Service**: RunComfy

## 📞 Support

- **Documentation**: See the docs folder
- **Issues**: Check TESTING_CHECKLIST.md for troubleshooting
- **Blender Console**: Window → Toggle System Console for debug output

## 🎉 Acknowledgments

Built with:
- Blender Python API
- RunComfy AI services
- Love for creative workflows

---

**Status**: Production-ready with LoRa and UV Texture support  
**Version**: 0.3.3  
**Last Updated**: December 29, 2025

---

*Transform your 3D workflow with AI-powered real-time visualization* ✨

