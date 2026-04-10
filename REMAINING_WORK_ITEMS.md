# Remaining Work Items - MiroFish

**Last Updated**: 2026-04-10  
**Current Version**: v0.5.2  
**Container Status**: ✅ Updated and Running

---

## ✅ Completed (Recent)

| Item | Status | Date |
|------|--------|------|
| Upstream sync with security fixes | ✅ | 2026-04-10 |
| i18n migration (all views) | ✅ | 2026-04-10 |
| English language support verified | ✅ | 2026-04-10 |
| Container updated with latest code | ✅ | 2026-04-10 |

---

## 🔴 Critical (Fix Immediately)

### 1. Backend Test Failure
- **File**: `backend/tests/test_graph_builder.py`
- **Issue**: `test_build_graph_returns_group_id` fails due to ontology format mismatch
- **Impact**: Low (production code works, test needs update)
- **Effort**: 15 minutes
- **Action**: Update test mock data to match new ontology structure

```python
# Current test expects:
ontology = {"entity_types": [{"name": "Person", ...}]}

# Should expect:
ontology = {"entities": [{"name": "Person", ...}]}
```

---

## 🟠 High Priority (This Week)

### 2. Complete Component i18n Migration
**Files Needing Migration**:
- [ ] `frontend/src/components/Step2EnvSetup.vue` (95 $t() calls but still has hardcoded text)
- [ ] `frontend/src/components/Step4Report.vue` (2 $t() calls, needs more)
- [ ] `frontend/src/components/Step5Interaction.vue` (33 $t() calls, needs verification)
- [ ] `frontend/src/components/GraphPanel.vue` (Chinese comments, some hardcoded strings)
- [ ] `frontend/src/components/HistoryDatabase.vue` (Chinese comments)

**Impact**: Full English UI consistency  
**Effort**: 3-4 hours  
**Note**: Components work but have mixed languages in edge cases

### 3. Backend API Response Translation
**Files**:
- [ ] `backend/app/api/graph.py` - API response messages
- [ ] `backend/app/api/simulation.py` - Progress messages
- [ ] `backend/app/api/report.py` - Status messages

**Impact**: Backend returns English messages to frontend  
**Effort**: 2 hours  
**Implementation**: Use `from app.utils.locale import t` for translations

### 4. LLM Prompt Language Injection
**Files**:
- [ ] `backend/app/services/ontology_generator.py`
- [ ] `backend/app/services/report_agent.py`
- [ ] `backend/app/services/simulation_config_generator.py`

**Impact**: LLM responds in user's selected language  
**Effort**: 1 hour  
**Implementation**: Add `get_language_instruction()` to prompts

---

## 🟡 Medium Priority (This Month)

### 5. End-to-End Testing
**Test Scenarios**:
- [ ] Upload PDF document → Generate ontology
- [ ] Build graph → Verify entities/relationships
- [ ] Configure simulation → Start simulation
- [ ] Run simulation → Monitor progress
- [ ] Generate report → Download/view
- [ ] Agent chat → Interactive conversation
- [ ] Language switching → EN ↔ ZH

**Impact**: Verify all features work correctly  
**Effort**: 2-3 hours  
**Tools**: Manual testing + existing pytest suite

### 6. Documentation Updates
**Files to Update**:
- [ ] `README.md` - Add i18n features, sync mechanism
- [ ] `CHANGELOG.md` - Document v0.5.2 changes
- [ ] `API.md` (create) - API endpoint documentation
- [ ] `DEPLOYMENT.md` (create) - Deployment guide

**Impact**: Better onboarding for new users  
**Effort**: 4 hours

### 7. Error Handling Improvements
**Areas**:
- [ ] Frontend error boundaries
- [ ] Backend error response standardization
- [ ] User-friendly error messages
- [ ] Retry logic for network failures

**Impact**: Better user experience during failures  
**Effort**: 3-4 hours

### 8. Performance Optimization
**Tasks**:
- [ ] Lazy load translation files (currently eager loaded)
- [ ] Optimize bundle size (currently 460KB JS)
- [ ] Add service worker for offline support
- [ ] Graph rendering optimization for large datasets

**Impact**: Faster load times, better UX  
**Effort**: 6-8 hours

---

## 🟢 Low Priority (Next 3 Months)

### 9. Simulation Templates
**Templates to Create**:
- [ ] Election simulation (voter opinion dynamics)
- [ ] Product launch (market reception)
- [ ] Crisis management (PR disaster response)
- [ ] Viral marketing (social media spread)
- [ ] Policy change (public reaction)

**Impact**: Faster user onboarding  
**Effort**: 8 hours

### 10. Advanced Features
**Features**:
- [ ] Dark mode theme
- [ ] Keyboard shortcuts
- [ ] Export to PDF/Word
- [ ] Real-time collaboration
- [ ] WebSocket for live updates

**Impact**: Modern UX, competitive features  
**Effort**: 20+ hours

### 11. Testing Infrastructure
**Tasks**:
- [ ] Frontend unit tests (Vue Test Utils)
- [ ] E2E tests (Playwright/Cypress)
- [ ] Backend integration tests
- [ ] Performance benchmarks

**Impact**: Code quality, regression prevention  
**Effort**: 12 hours

### 12. Monitoring & Analytics
**Features**:
- [ ] Application metrics (Prometheus/Grafana)
- [ ] User analytics (privacy-respecting)
- [ ] Error tracking (Sentry)
- [ ] Usage statistics

**Impact**: Operational visibility  
**Effort**: 6 hours

---

## 📋 Quick Fixes (15-30 Minutes Each)

| # | Item | File | Description |
|---|------|------|-------------|
| 1 | Fix test | `test_graph_builder.py` | Update ontology mock data |
| 2 | Add favicon | `frontend/public/` | Add proper favicon.ico |
| 3 | Update title | `frontend/index.html` | Dynamic title based on locale |
| 4 | Add 404 page | `frontend/src/views/` | NotFound.vue for invalid routes |
| 5 | Loading states | `frontend/src/components/` | Consistent loading indicators |
| 6 | Toast notifications | `frontend/src/` | Global notification system |

---

## 🎯 Recommended Next Steps

### Option A: Stability Focus (Recommended)
1. Fix the failing test (#1)
2. Complete component i18n (#2)
3. End-to-end testing (#5)
4. Documentation updates (#6)

**Timeline**: 1 week  
**Result**: Production-ready, stable application

### Option B: Feature Focus
1. Simulation templates (#9)
2. Dark mode (#10)
3. Export functionality (#10)
4. Testing infrastructure (#11)

**Timeline**: 3 weeks  
**Result**: Feature-rich application

### Option C: Performance Focus
1. Lazy loading (#8)
2. Bundle optimization (#8)
3. Service worker (#8)
4. Graph optimization (#8)

**Timeline**: 2 weeks  
**Result**: Fast, optimized application

---

## 📊 Current Status Summary

| Category | Status | Notes |
|----------|--------|-------|
| **Core Features** | ✅ Stable | Graphiti, Simulation, Reports working |
| **i18n** | ✅ 90% Complete | All major views done, components pending |
| **Tests** | ⚠️ 96% | 1 failing test (non-critical) |
| **Documentation** | ⚠️ Basic | Needs API docs, deployment guide |
| **Performance** | ⚠️ Good | Room for optimization |
| **Security** | ✅ Current | Latest dependencies |

---

## 🐛 Known Issues

| Issue | Severity | Workaround | Fix Planned |
|-------|----------|------------|-------------|
| Test failure | Low | Ignore for now | Yes - #1 |
| Bundle size | Medium | None | Yes - #8 |
| Missing 404 page | Low | Redirects to home | No |
| No offline support | Low | Requires network | Yes - #8 |

---

## 💡 Suggestions from Code Review

1. **Add TypeScript**: Gradual migration for better type safety
2. **Pin dependencies**: Use exact versions in package.json
3. **Add pre-commit hooks**: Linting, formatting before commits
4. **Container health checks**: Add to docker-compose.yml
5. **Backup strategy**: Document Neo4j backup procedure

---

## 📝 Container Update Notes

**Current Container**: `localhost/mirofish:v0.5.1`  
**Update Method**: Volume-mounted current code  
**Status**: ✅ Running with latest code  
**Access**: http://localhost:3005 (frontend), http://localhost:5001 (backend)

**To rebuild image fully** (when ready):
```bash
cd /var/home/bahram/local-repos/MiroFish
podman build -t localhost/mirofish:v0.5.2 .
podman stop mirofish
podman run -d --name mirofish --replace --network host \
  -p 3000:3000 -p 5001:5001 \
  -v "$PWD/.env:/app/.env:Z" \
  localhost/mirofish:v0.5.2
```

---

**Next Action Recommended**: Fix the failing test (#1) - 15 minutes
