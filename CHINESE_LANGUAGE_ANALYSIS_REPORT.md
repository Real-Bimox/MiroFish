# Chinese Language Elements Analysis Report
## MiroFish Repository

**Generated:** March 21, 2026  
**Total Lines with Chinese:** 3,602  
**Files Affected:** 37

---

## Executive Summary

This report identifies all Chinese language elements in the MiroFish codebase and evaluates the impact of translating them to English.

### Key Findings:
1. **3,530 lines** in backend Python files contain Chinese (98% of all Chinese content)
2. **39 lines** in frontend JavaScript files contain Chinese
3. **22 lines** in documentation files contain Chinese
4. **1 line** in config files contains Chinese

---

## Impact Assessment by Category

### 1. 🔴 HIGH IMPACT - Code Comments & Docstrings (Critical)
**Affected Files:** 24 Python files  
**Estimated Lines:** ~2,000+ lines

**Description:**
Extensive Chinese comments and docstrings throughout the backend codebase. These serve as the primary documentation for developers.

**Translation Impact:**
- **Pros:** Better accessibility for international developers
- **Cons:** Large effort required; may lose nuances in translation
- **Risk:** LOW - Comments don't affect runtime behavior

**Examples Found:**
```python
# backend/app/api/graph.py
图谱相关API路由  # Graph-related API routes
采用项目上下文机制，服务端持久化状态  # Uses project context mechanism, server-side persistent state
获取项目详情  # Get project details
项目不存在  # Project does not exist
```

**Recommendation:** 
Priority translation - essential for code maintainability by international teams.

---

### 2. 🔴 HIGH IMPACT - User-Facing Error Messages (Critical)
**Affected Files:** API route files  
**Estimated Lines:** ~200+ lines

**Description:**
Chinese error messages returned to users through API responses.

**Examples Found:**
```python
# backend/app/api/graph.py:163
"error": "请提供模拟需求描述 (simulation_requirement)"

# backend/app/api/graph.py:171
"error": "请至少上传一个文档文件"

# backend/app/api/graph.py:312
"error": f"项目不存在: {project_id}"

# backend/app/api/simulation.py:304
# - ready: 准备完成，可以运行
# - preparing: 如果 config_generated=True 说明已完成
```

**Translation Impact:**
- **Pros:** Better UX for English-speaking users
- **Cons:** Breaking change for existing Chinese-speaking users
- **Risk:** MEDIUM - Changes user experience significantly

**Recommendation:**
CRITICAL priority - these directly impact end users. Consider i18n framework for multi-language support.

---

### 3. 🟡 MEDIUM IMPACT - Logging Messages
**Affected Files:** Multiple service files  
**Estimated Lines:** ~800+ lines

**Description:**
Chinese log messages used for debugging and monitoring.

**Examples Found:**
```python
# backend/app/api/graph.py
logger.info("=== 开始生成本体定义 ===")
logger.info(f"文本提取完成，共 {len(all_text)} 字符")
logger.info(f"本体生成完成: {entity_count} 个实体类型, {edge_count} 个关系类型")

# backend/app/services/simulation_runner.py
logger.info(f"[进程内运行] {platform} 模拟完成")
```

**Translation Impact:**
- **Pros:** Consistent with English log aggregation systems
- **Cons:** Harder for Chinese-speaking developers to debug
- **Risk:** LOW - Internal diagnostics only

**Recommendation:**
Medium priority - nice to have for consistency but not user-facing.

---

### 4. 🟡 MEDIUM IMPACT - Progress/Status Messages
**Affected Files:** simulation.py, report.py  
**Estimated Lines:** ~150 lines

**Description:**
Chinese status messages shown during long-running operations.

**Examples Found:**
```python
# backend/app/api/simulation.py
"reading": "读取图谱实体",
"generating_profiles": "生成Agent人设",
"generating_config": "生成模拟配置",
"copying_scripts": "准备模拟脚本"

message="初始化Report Agent..."
message="文本分块中..."
message=f"处理文本块 {processed}/{total}..."
```

**Translation Impact:**
- **Pros:** Better for English UI display
- **Cons:** Need to ensure frontend can handle both
- **Risk:** MEDIUM - Affects user-facing progress indicators

**Recommendation:**
High priority if frontend is English-only; implement i18n for best results.

---

### 5. 🟢 LOW IMPACT - Documentation Files
**Affected Files:** README.md, README-EN.md  
**Estimated Lines:** 22 lines

**Description:**
Chinese content in README files (mostly image filenames and links).

**Examples Found:**
```markdown
# README.md
[English](./README-EN.md) | [中文文档](./README.md)
<img src="./static/image/Screenshot/运行截图1.png" alt="Screenshot 1" width="100%"/>
<img src="./static/image/QQ群.png" alt="QQ Group" width="60%"/>
```

**Translation Impact:**
- **Pros:** Clean URLs, better for SEO
- **Cons:** Breaking image links; need to rename files
- **Risk:** LOW - Can maintain both language versions

**Recommendation:**
Keep dual-language READMEs; rename image files only if necessary.

---

### 6. 🟢 LOW IMPACT - Image/File References
**Affected Files:** README files  
**Estimated Lines:** 10 lines

**Description:**
Chinese filenames referenced in documentation.

**Examples Found:**
- `运行截图1.png` (Runtime Screenshot 1)
- `武大模拟演示封面.png` (Wuhan University Simulation Demo Cover)
- `红楼梦模拟推演封面.jpg` (Dream of Red Chamber Simulation Cover)
- `QQ群.png` (QQ Group)

**Translation Impact:**
- **Pros:** ASCII-safe filenames
- **Cons:** Need to rename actual files and update references
- **Risk:** LOW - Cosmetic change

**Recommendation:**
Optional - rename files for consistency but not critical.

---

### 7. 🟢 LOW IMPACT - Frontend API Comments
**Affected Files:** frontend/src/api/*.js  
**Estimated Lines:** 39 lines

**Description:**
Chinese comments in frontend JavaScript API files.

**Examples Found:**
```javascript
// frontend/src/api/simulation.js
// 创建模拟
// 准备模拟
// 查询准备状态
```

**Translation Impact:**
- **Pros:** Consistent with English codebase
- **Cons:** Minimal - frontend is thin layer
- **Risk:** VERY LOW - Comments only

**Recommendation:**
Low priority - translate as part of general cleanup.

---

## Detailed File-by-File Analysis

### Backend API Files

| File | Chinese Lines | Category | Translation Priority |
|------|---------------|----------|---------------------|
| `backend/app/api/simulation.py` | 487 | API routes, error messages, docstrings | 🔴 CRITICAL |
| `backend/app/api/report.py` | 149 | API routes, error messages, docstrings | 🔴 CRITICAL |
| `backend/app/api/graph.py` | 106 | API routes, error messages, docstrings | 🔴 CRITICAL |

### Backend Service Files

| File | Chinese Lines | Category | Translation Priority |
|------|---------------|----------|---------------------|
| `backend/app/services/report_agent.py` | 670 | Agent prompts, logs, messages | 🔴 CRITICAL |
| `backend/app/services/oasis_profile_generator.py` | 286 | Profile generation, comments | 🟡 MEDIUM |
| `backend/app/services/simulation_runner.py` | 348 | Runner logs, status messages | 🟡 MEDIUM |
| `backend/app/services/ontology_generator.py` | 136 | Ontology generation, comments | 🟡 MEDIUM |
| `backend/app/services/simulation_config_generator.py` | 255 | Config generation, comments | 🟡 MEDIUM |
| `backend/app/services/simulation_manager.py` | 91 | Management messages | 🟡 MEDIUM |
| `backend/app/services/simulation_ipc.py` | 72 | IPC messages | 🟡 MEDIUM |

### Backend Model/Util Files

| File | Chinese Lines | Category | Translation Priority |
|------|---------------|----------|---------------------|
| `backend/app/models/project.py` | 50 | Model docstrings | 🟡 MEDIUM |
| `backend/app/models/task.py` | 37 | Model docstrings | 🟡 MEDIUM |
| `backend/app/utils/file_parser.py` | 38 | Parser comments | 🟢 LOW |
| `backend/app/utils/llm_client.py` | 18 | Client comments | 🟢 LOW |
| `backend/app/utils/logger.py` | 24 | Logger setup | 🟢 LOW |
| `backend/app/utils/retry.py` | 35 | Retry logic comments | 🟢 LOW |

### Backend Scripts

| File | Chinese Lines | Category | Translation Priority |
|------|---------------|----------|---------------------|
| `backend/scripts/run_parallel_simulation.py` | 306 | Simulation runner script | 🟡 MEDIUM |
| `backend/scripts/run_twitter_simulation.py` | 152 | Twitter simulation | 🟡 MEDIUM |
| `backend/scripts/run_reddit_simulation.py` | 130 | Reddit simulation | 🟡 MEDIUM |
| `backend/scripts/action_logger.py` | 34 | Logging utilities | 🟢 LOW |
| `backend/scripts/test_profile_format.py` | 35 | Test utilities | 🟢 LOW |

### Frontend Files

| File | Chinese Lines | Category | Translation Priority |
|------|---------------|----------|---------------------|
| `frontend/src/api/simulation.js` | 29 | API comments | 🟢 LOW |
| `frontend/src/api/index.js` | 8 | API comments | 🟢 LOW |
| `frontend/src/store/pendingUpload.js` | 2 | Store comments | 🟢 LOW |

### Documentation

| File | Chinese Lines | Category | Translation Priority |
|------|---------------|----------|---------------------|
| `README.md` | 10 | Documentation, image refs | 🟢 LOW |
| `README-EN.md` | 10 | Documentation, image refs | 🟢 LOW |
| `docs/superpowers/plans/*.md` | 2 | Planning docs | 🟢 LOW |

---

## Translation Strategy Recommendations

### Option 1: Full Internationalization (Recommended)
Implement proper i18n framework:
- Use Python's `gettext` or a JSON-based i18n system
- Support both Chinese and English
- Allow runtime language switching
- Estimated effort: **3-5 days**

### Option 2: English-Only Conversion
Translate all Chinese to English:
- Update all comments, logs, and messages
- Rename image files with Chinese names
- Single language codebase
- Estimated effort: **2-3 days**

### Option 3: Phased Translation (Pragmatic)
Translate in phases by priority:
1. **Phase 1:** User-facing error messages and API responses (1 day)
2. **Phase 2:** Progress/status messages (0.5 day)
3. **Phase 3:** Documentation and comments (ongoing)

### Option 4: Maintain Status Quo
Keep Chinese content as-is:
- Document that codebase is Chinese-primary
- Provide separate English documentation
- Minimal effort but limits international adoption

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking user experience for Chinese users | HIGH | Implement i18n with language switching |
| Losing nuance in technical translations | MEDIUM | Use technical review process |
| Breaking image references | LOW | Rename files carefully, test all links |
| Inconsistent terminology | MEDIUM | Create glossary before translating |
| Large effort required | MEDIUM | Prioritize user-facing content first |

---

## Conclusion

The MiroFish codebase contains significant Chinese language elements (3,602 lines across 37 files), primarily in:
1. **Backend API layer** - error messages and docstrings
2. **Service layer** - logging and status messages
3. **Documentation** - README files and image references

**Recommended Approach:**
Implement **Option 1 (Full i18n)** for user-facing content and **Option 3 (Phased)** for internal comments. This provides:
- Immediate value to English-speaking users
- Maintains support for existing Chinese users
- Allows gradual migration of internal documentation

---

## Appendix: Sample Translations

### Error Messages
| Chinese | English Translation |
|---------|---------------------|
| 项目不存在 | Project not found |
| 请提供模拟需求描述 | Please provide simulation requirement description |
| 请至少上传一个文档文件 | Please upload at least one document file |
| 配置错误 | Configuration error |
| 图谱构建任务已启动 | Graph build task started |

### Log Messages
| Chinese | English Translation |
|---------|---------------------|
| 开始生成本体定义 | Starting ontology generation |
| 文本提取完成 | Text extraction completed |
| 构建图谱 | Building graph |
| 处理文本块 | Processing text chunk |

### Status Messages
| Chinese | English Translation |
|---------|---------------------|
| 读取图谱实体 | Reading graph entities |
| 生成Agent人设 | Generating agent profiles |
| 生成模拟配置 | Generating simulation config |
| 准备模拟脚本 | Preparing simulation scripts |

---

*Report generated by automated analysis - March 21, 2026*
