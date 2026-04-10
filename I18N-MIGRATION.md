# i18n Migration Summary

## Overview

Successfully migrated from hardcoded English translations to a proper vue-i18n internationalization system. This aligns your fork with upstream's i18n architecture and makes future syncs much easier.

## What Was Done

### 1. Core Infrastructure
- ✅ Installed `vue-i18n@^11.3.0` in frontend
- ✅ Created `frontend/src/i18n/index.js` with dynamic locale loading
- ✅ Created `frontend/src/components/LanguageSwitcher.vue` for UI language switching
- ✅ Updated `frontend/src/main.js` to initialize i18n plugin
- ✅ Updated `frontend/index.html` to set `lang` attribute before Vue mounts
- ✅ Updated `frontend/src/api/index.js` to send `Accept-Language` header

### 2. Translation Files
- ✅ Created `locales/en.json` - English translations
- ✅ Created `locales/zh.json` - Chinese translations  
- ✅ Created `locales/languages.json` - Language registry

### 3. Backend Support
- ✅ Created `backend/app/utils/locale.py` with translation utilities
- ✅ Support for `Accept-Language` header detection
- ✅ Thread-local storage for locale in background tasks
- ✅ `t()` function for backend translations

### 4. Component Migration
- ✅ Migrated `Home.vue` - All hero text, buttons, labels
- ✅ Migrated `MainView.vue` - View modes, step names, status texts
- ✅ Added `LanguageSwitcher` to navbar in both views

## File Structure

```
MiroFish/
├── locales/                          # Translation files (shared)
│   ├── en.json                       # English translations
│   ├── zh.json                       # Chinese translations
│   └── languages.json                # Language registry
├── frontend/
│   ├── src/
│   │   ├── i18n/
│   │   │   └── index.js              # i18n configuration
│   │   ├── components/
│   │   │   └── LanguageSwitcher.vue  # Language switch UI
│   │   ├── views/
│   │   │   ├── Home.vue              # Migrated ✓
│   │   │   └── MainView.vue          # Migrated ✓
│   │   ├── api/
│   │   │   └── index.js              # Updated with Accept-Language
│   │   └── main.js                   # i18n plugin initialization
│   └── index.html                    # Dynamic lang attribute
└── backend/
    └── app/
        └── utils/
            └── locale.py             # Backend translation utilities
```

## How to Use

### Switching Languages
1. The language switcher appears in the top-right corner of the navbar
2. Click "English" or "中文" to switch languages
3. The preference is saved to localStorage and persists across sessions

### Adding New Translations

1. **Add new keys to translation files** (`locales/en.json`, `locales/zh.json`):
```json
{
  "section": {
    "newKey": "Translation text"
  }
}
```

2. **Use in Vue templates**:
```vue
<template>
  <p>{{ $t('section.newKey') }}</p>
  <p>{{ $t('section.dynamicKey', { value: 42 }) }}</p>
</template>
```

3. **Use in Vue script**:
```javascript
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const message = t('section.newKey')
```

4. **Use in backend Python**:
```python
from app.utils.locale import t

message = t('section.newKey')
message_with_param = t('section.dynamicKey', value=42)
```

## Remaining Work (Optional)

The following components still have hardcoded strings and can be migrated as needed:

### High Priority
- `Process.vue` - Large file with many UI strings
- `SimulationView.vue` - Simulation interface
- `SimulationRunView.vue` - Running simulation display
- `ReportView.vue` - Report display
- `InteractionView.vue` - Chat interface

### Medium Priority
- Step components in `frontend/src/components/`:
  - `Step1GraphBuild.vue`
  - `Step2EnvSetup.vue`
  - `Step3SimulationRun.vue` (if exists)
  - `Step4Report.vue` (if exists)
  - `Step5Interaction.vue` (if exists)
- `GraphPanel.vue` - Graph visualization panel
- `HistoryDatabase.vue` - History records display

### Backend Priority
- API response messages in `backend/app/api/` routes
- Progress messages in background tasks
- LLM prompt templates (inject language instruction)

## Migration Pattern

For each remaining file, follow this pattern:

### 1. Replace Hardcoded Strings
```vue
<!-- Before -->
<button>Start Engine</button>
<p>Graph View Build</p>

<!-- After -->
<button>{{ $t('home.startEngine') }}</button>
<p>{{ $t('step1.title') }}</p>
```

### 2. Handle Dynamic Values
```vue
<!-- Before -->
<p>Step {{ step }}/5</p>

<!-- After -->
<p>{{ $t('nav.step', { step: currentStep }) }}</p>
```

### 3. HTML Content (v-html)
```vue
<!-- For HTML in translations -->
<p v-html="$t('home.heroDesc', { 
  brand: '<span class=\"highlight\">MiroFish</span>',
  agentScale: '<span class=\"highlight\">millions</span>'
})"></p>
```

## Benefits of This Migration

1. **Easier Upstream Syncs**: Upstream's changes to translations will merge cleanly
2. **Multi-language Support**: Can easily add Spanish, French, etc.
3. **Consistent Architecture**: Matches upstream's design patterns
4. **LLM Integration**: Backend can send language instructions to LLMs
5. **User Preference**: Users can switch languages without reloading

## Testing

After pulling these changes:

1. Install dependencies:
   ```bash
   cd frontend && npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Verify:
   - Language switcher appears in navbar
   - Clicking language buttons changes UI text
   - Preference persists after page reload
   - API requests include `Accept-Language` header

## Next Steps

1. **Complete component migration** as needed for your use case
2. **Sync with upstream** using the provided sync mechanism
3. **Add more languages** by creating new files in `locales/`
4. **Update LLM prompts** to use `get_language_instruction()` from locale.py

---

**Migration Date**: 2026-04-10  
**Status**: Core infrastructure complete, component migration ongoing  
**Compatibility**: Aligns with upstream 666ghj/MiroFish i18n system
