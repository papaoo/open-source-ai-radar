// Client-side i18n for Open Source AI Radar (static site, no routing).
// UI chrome only — repository names/descriptions stay in their original English.

export type Lang = "en" | "zh";

export const LANG_STORAGE_KEY = "radar-lang";

// Fixed AI-category display names. Data/URLs keep the English slug; only the
// rendered label is swapped, so a finite, curated mapping is enough (no MT).
export const catMap: Record<string, string> = {
  "Evaluation & Benchmarks": "评测与基准",
  "AI Agents": "AI 智能体",
  "AI Coding Tools": "AI 编程工具",
  "AI Infrastructure": "AI 基础设施",
  "Generative AI": "生成式 AI",
  MCP: "MCP 协议",
  "AI Safety & Alignment": "AI 安全与对齐",
  "Local AI": "本地 AI",
  RAG: "RAG 检索增强",
  "LLM Frameworks": "大模型框架",
  "Multimodal AI": "多模态 AI",
  Uncategorized: "未分类",
};

// Maturity stage labels. Data keeps the English enum; only the rendered value
// is swapped (finite set, curated — same principle as catMap, no MT needed).
export const maturityMap: Record<string, string> = {
  Emerging: "新兴",
  Growing: "成长期",
  Mature: "成熟",
  Declining: "衰退",
  Unknown: "未知",
};

// Sub-category labels from config/categories.yml. Lookup is case-insensitive so
// free-form/DB-cased values (e.g. "image" vs "Image") still map; unknown values
// fall back to the original (treated like a proper noun).
export const subCatMap: Record<string, string> = {
  Server: "服务端",
  Client: "客户端",
  Tool: "工具",
  Integration: "集成",
  "Vector Database": "向量数据库",
  "RAG Framework": "RAG 框架",
  Embeddings: "嵌入",
  "Knowledge Management": "知识管理",
  "CLI Tool": "命令行工具",
  "IDE Extension": "IDE 扩展",
  "Code Completion": "代码补全",
  "Code Review": "代码审查",
  Guardrails: "护栏",
  "Content Filtering": "内容过滤",
  "Bias Detection": "偏差检测",
  "Alignment Research": "对齐研究",
  Benchmark: "基准测试",
  "Evaluation Framework": "评测框架",
  "Comparison Tool": "对比工具",
  Image: "图像",
  Video: "视频",
  Audio: "音频",
  "3D": "3D",
  "Vision-Language": "视觉-语言",
  "Audio-Language": "音频-语言",
  "Omni-modal": "全模态",
  "Local Runner": "本地运行器",
  "Privacy Tool": "隐私工具",
  "Edge AI": "边缘 AI",
  "Offline AI": "离线 AI",
  "Model Serving": "模型服务",
  "GPU Management": "GPU 管理",
  Orchestration: "编排",
  Monitoring: "监控",
  "Coding Agent": "编程智能体",
  "Research Agent": "研究智能体",
  "Task Agent": "任务智能体",
  "Conversational Agent": "对话智能体",
  "Inference Engine": "推理引擎",
  "Fine-tuning": "微调",
  Quantization: "量化",
  Serving: "服务化",
};

// Opportunity tier labels. Data keeps the English slug (blue_ocean etc.); only
// the rendered badge is swapped (finite curated set — same principle as catMap).
export const tierMap: Record<string, string> = {
  blue_ocean: "蓝海机会",
  high_potential: "高潜力",
  watch: "观察",
};

// Registries addressable by `data-i18n-map` var-name -> kind. Used to localize
// dynamic values embedded inside translated sentences (category, maturity,
// sub-category) without machine translation.
const VAR_MAPS: Record<string, Record<string, string>> = {
  category: catMap,
  maturity: maturityMap,
  subcategory: subCatMap,
  tier: tierMap,
};

type Entry = { en: string; zh: string };

// Flat dictionary keyed by dot-namespaced ids. Kept flat for O(1) lookup and
// simple data-i18n attribute matching.
export const dict: Record<string, Entry> = {
  // ── Navigation & footer ──
  "nav.home": { en: "Home", zh: "首页" },
  "nav.rankings": { en: "Rankings", zh: "排名" },
  "nav.trending": { en: "Trending", zh: "趋势" },
  "nav.breakouts": { en: "Breakouts", zh: "突破" },
  "nav.opportunities": { en: "Opportunities", zh: "商机" },
  "nav.categories": { en: "Categories", zh: "分类" },
  "nav.digests": { en: "Digests", zh: "周报" },
  "nav.api": { en: "API", zh: "API" },
  "nav.toggleMenu": { en: "Toggle menu", zh: "切换菜单" },
  "nav.github": { en: "GitHub", zh: "GitHub" },

  // ── Language / theme controls ──
  "lang.toggle": { en: "中文", zh: "EN" }, // shows the *other* language
  "lang.aria": { en: "Switch language", zh: "切换语言" },
  "theme.light": { en: "Light", zh: "浅色" },
  "theme.dark": { en: "Dark", zh: "深色" },
  "theme.toggle": { en: "Toggle theme", zh: "切换主题" },

  // ── Home ──
  "home.titlePrefix": { en: "Discover", zh: "发现" },
  "home.titleAccent": { en: "momentum", zh: "势能动向" },
  "home.titleSuffix": { en: "in open-source AI", zh: "于开源 AI 之间" },
  "home.subtitle": {
    en: "Track 9,000+ projects scored by impact, velocity, and health. Updated daily.",
    zh: "以影响力、速度、健康度为 9000+ 个项目评分，每日更新。",
  },
  "stat.projects": { en: "Projects Tracked", zh: "追踪项目" },
  "stat.stars": { en: "Total Stars", zh: "总 Star 数" },
  "stat.languages": { en: "Languages", zh: "编程语言" },
  "stat.categories": { en: "AI Categories", zh: "AI 分类" },

  "section.breakouts": { en: "Breakout Candidates", zh: "突破候选" },
  "section.opportunities": { en: "Latest Opportunities", zh: "最新机会" },
  "section.allOpportunities": { en: "All opportunities", zh: "全部机会" },
  "section.viewAll": { en: "View all", zh: "查看全部" },
  "section.categories": { en: "AI Categories", zh: "AI 分类" },
  "section.explore": { en: "Explore", zh: "浏览" },
  "section.topRanked": { en: "Top Ranked", zh: "热门排行" },
  "section.fullRankings": { en: "Full rankings", zh: "完整排名" },
  "section.risingFast": { en: "Rising Fast", zh: "急速上升" },
  "section.allTrending": { en: "All trending", zh: "全部趋势" },

  // ── Momentum states ──
  "momentum.breakout": { en: "Breakout", zh: "爆发" },
  "momentum.accelerating": { en: "Accelerating", zh: "加速" },
  "momentum.rising": { en: "Rising", zh: "上升" },
  "momentum.stable": { en: "Stable", zh: "平稳" },
  "momentum.declining": { en: "Declining", zh: "回落" },

  // ── Common metrics / labels ──
  "label.stars": { en: "stars", zh: "stars" },
  "label.velocity": { en: "Velocity", zh: "速度" },
  "label.score": { en: "Score", zh: "评分" },
  "label.impact": { en: "Impact", zh: "影响力" },
  "label.health": { en: "Health", zh: "健康度" },
  "label.accel": { en: "accel", zh: "加速" },
  "label.vel": { en: "vel", zh: "速度" },
  "label.projects": { en: "projects", zh: "个项目" },
  "label.uncategorized": { en: "Uncategorized", zh: "未分类" },

  // ── Rankings (top) page ──
  "rankings.titlePrefix": { en: "Project", zh: "项目" },
  "rankings.titleAccent": { en: "Rankings", zh: "排行榜" },
  "rankings.subtitle": {
    en: "All {n} tracked projects ranked by radar score",
    zh: "全部 {n} 个项目按雷达评分排序",
  },
  "search.placeholder": { en: "Search projects...", zh: "搜索项目..." },
  "filter.all": { en: "All", zh: "全部" },
  "table.rank": { en: "#", zh: "#" },
  "table.project": { en: "Project", zh: "项目" },
  "table.language": { en: "Language", zh: "语言" },
  "table.stars": { en: "Stars", zh: "Stars" },
  "table.score": { en: "Score", zh: "评分" },
  "table.trend": { en: "Trend", zh: "走势" },
  "table.velocity": { en: "Velocity", zh: "速度" },
  "table.momentum": { en: "Momentum", zh: "动量" },
  "count.showingAll": { en: "Showing all {n} projects", zh: "显示全部 {n} 个项目" },
  "count.showingOf": {
    en: "Showing {shown} of {total} projects",
    zh: "显示 {total} 个中的 {shown} 个",
  },

  // ── Project detail page ──
  "proj.scoringBreakdown": { en: "Scoring Breakdown", zh: "评分构成" },
  "proj.growthMetrics": { en: "Growth Metrics", zh: "增长指标" },
  "proj.starHistory": { en: "Star History", zh: "Star 走势" },
  "proj.scoreHistory": { en: "Radar Score History", zh: "雷达评分走势" },
  "proj.whyRanks": { en: "Why it ranks", zh: "评分解读" },
  "proj.viewOnGitHub": { en: "View on GitHub", zh: "在 GitHub 查看" },
  "proj.forks": { en: "Forks", zh: "Fork 数" },
  "proj.radarScore": { en: "Radar Score", zh: "雷达评分" },
  "proj.momentum": { en: "Momentum", zh: "动量" },
  "proj.oppCard": { en: "Opportunity Assessment", zh: "机会评估" },
  "proj.oppCardHint": {
    en: "An early, under-priced bet: strong leading indicators with manageable risk.",
    zh: "尚未被主流定价的早期机会：领先信号强劲且风险可控。",
  },

  // ── Compare page ──
  "compare.titlePrefix": { en: "Compare", zh: "项目" },
  "compare.titleAccent": { en: "Projects", zh: "对比" },
  "compare.subtitle": {
    en: "Pick two or three projects and see how they stack up",
    zh: "选择两到三个项目，查看它们的对比表现",
  },
  "compare.slot1": { en: "Search repo 1...", zh: "搜索项目 1..." },
  "compare.slot2": { en: "Search repo 2...", zh: "搜索项目 2..." },
  "compare.slot3": { en: "Search repo 3 (optional)...", zh: "搜索项目 3（可选）..." },
  "compare.btn": { en: "Compare", zh: "对比" },
  "compare.enableJs": { en: "Enable JavaScript to use the comparison tool.", zh: "请启用 JavaScript 以使用对比工具。" },
  "compare.needTwo": {
    en: "Select at least two projects to compare.",
    zh: "请至少选择两个项目进行对比。",
  },
  "compare.loaded": { en: "{n} projects loaded — start typing above", zh: "已加载 {n} 个项目 — 在上方开始输入" },
  "compare.category": { en: "Category", zh: "分类" },
  "compare.language": { en: "Language", zh: "语言" },
  "compare.license": { en: "License", zh: "许可证" },
  "compare.none": { en: "None", zh: "无" },
  "compare.stars": { en: "Stars", zh: "Stars" },
  "compare.forks": { en: "Forks", zh: "Fork 数" },
  "compare.radarScore": { en: "Radar Score", zh: "雷达评分" },
  "compare.impact": { en: "Impact", zh: "影响力" },
  "compare.velocity": { en: "Velocity", zh: "速度" },
  "compare.health": { en: "Health", zh: "健康度" },
  "compare.age": { en: "Age", zh: "项目年龄" },
  "compare.lastPush": { en: "Last Push", zh: "最近推送" },

  // ── Trending page ──
  "trending.accent": { en: "Trending", zh: "趋势" },
  "trending.suffix": { en: "Projects", zh: "项目" },
  "trending.subtitle": { en: "Projects gaining the most momentum this week", zh: "本周动量增长最快的项目" },

  // ── Breakouts page ──
  "breakouts.accent": { en: "Breakout", zh: "突破" },
  "breakouts.suffix": { en: "Candidates", zh: "候选" },
  "breakouts.subtitle": { en: "Projects showing early signs of explosive growth", zh: "显露爆发早期迹象的项目" },
  "breakouts.acceleration": { en: "Acceleration", zh: "加速度" },
  "breakouts.emptyTitle": { en: "No breakouts detected yet", zh: "暂未检测到突破" },

  // ── Opportunities (机会指数) page ──
  "opp.accent": { en: "Opportunity", zh: "机会" },
  "opp.suffix": { en: "Index", zh: "指数" },
  "opp.subtitle": {
    en: "Under-priced bets with strong leading signals — early, accelerating, and sustainable",
    zh: "尚未被主流定价的机会 — 具备早期、加速与可持续的强劲领先信号",
  },
  "opp.scoreLabel": { en: "Opportunity Score", zh: "机会评分" },
  "opp.tierLabel": { en: "Tier: {v}", zh: "分档：{v}" },
  "opp.leadingSignals": { en: "Leading signals", zh: "领先信号" },
  "opp.early": { en: "Earliness", zh: "早期性" },
  "opp.momentum": { en: "Momentum", zh: "增长动量" },
  "opp.acceleration": { en: "Acceleration", zh: "加速度" },
  "opp.contributorPull": { en: "Contributor pull", zh: "开发者拉动" },
  "opp.viability": { en: "Viability", zh: "可持续性" },
  "opp.tailwind": { en: "Category tailwind", zh: "赛道风口" },
  "opp.whitespaceComp": { en: "Whitespace", zh: "空白度" },
  "opp.contributors7d": { en: "New contributors / 7d", zh: "7 天新增贡献者" },
  "opp.starsLabel": { en: "Stars", zh: "星标" },
    "opp.briefLabel": { en: "Opportunity brief:", zh: "机会简报：" },
  "opp.whitespaceTitle": { en: "Whitespace Categories", zh: "空白赛道" },
  "opp.whitespaceSubtitle": {
    en: "High-momentum categories with few tracked projects",
    zh: "动量高但在库项目稀少的赛道",
  },
  "opp.tracked": { en: "Tracked", zh: "在库" },
  "tier.blue_ocean": { en: "Blue Ocean", zh: "蓝海机会" },
  "tier.high_potential": { en: "High Potential", zh: "高潜力" },
  "tier.watch": { en: "Watch", zh: "观察" },
  "opp.emptyTitle": { en: "No opportunities detected yet", zh: "暂未发现机会" },
  "opp.empty": {
    en: "The opportunity index ranks early, fast-accelerating projects that stay healthy and show strong contributor pull. It refreshes as the pipeline collects new scores.",
    zh: "机会指数为早期、快速加速、同时保持健康且开发者拉动信号强劲的项目排名。随着流水线采集到新评分而自动更新。",
  },

  // ── Categories page ──
  "categories.prefix": { en: "AI", zh: "AI" },
  "categories.accent": { en: "Categories", zh: "分类" },
  "categories.subtitle": {
    en: "{n} categories tracked with momentum intelligence",
    zh: "共追踪 {n} 个分类，附带动量情报",
  },
  "categories.tracked": { en: "Tracked", zh: "已追踪" },
  "categories.avgScore": { en: "Avg Score", zh: "平均评分" },
  "categories.avgVelocity": { en: "Avg Velocity", zh: "平均速度" },
  "categories.avgHealth": { en: "Avg Health", zh: "平均健康度" },
  "categories.topProjects": { en: "Top Projects", zh: "热门项目" },

  // ── Category detail page ──
  "category.projectsTracked": { en: "{n} projects tracked", zh: "已追踪 {n} 个项目" },
  "category.empty": { en: "No projects found in this category yet.", zh: "该分类暂无项目。" },

  // ── Digests ──
  "digests.prefix": { en: "Weekly", zh: "每周" },
  "digests.accent": { en: "Digests", zh: "周报" },
  "digests.subtitle": {
    en: "{n} weeks of intelligence — risers, hidden gems, and momentum shifts",
    zh: "{n} 周情报 — 上升项目、意珠与动量变化",
  },
  "digests.tags": {
    en: "Top risers · hidden gems · new & promising · category shifts",
    zh: "热门上升 · 意珠 · 新兴潜力 · 分类变化",
  },
  "digests.empty": {
    en: "No digests published yet. The weekly report workflow generates one every week.",
    zh: "尚未发布周报。每周报告工作流会自动生成。",
  },
  "digest.weeklyDigests": { en: "Weekly Digests", zh: "每周周报" },
  "digest.notLoaded": { en: "This digest could not be loaded.", zh: "无法加载该周报。" },

  // ── Status page ──
  "status.prefix": { en: "System", zh: "系统" },
  "status.accent": { en: "Status", zh: "状态" },
  "status.subtitle": { en: "Pipeline health, data freshness, and workflow schedule", zh: "流水线健康度、数据新鲜度与工作流调度" },
  "status.checksPassing": { en: "{ok}/{total} checks passing", zh: "{ok}/{total} 项检查通过" },
  "status.lastSnapshot": { en: "Last Snapshot", zh: "最近快照" },
  "status.healthChecks": { en: "Health Checks", zh: "健康检查" },
  "status.database": { en: "Database", zh: "数据库" },
  "status.workflowSchedule": { en: "Workflow Schedule", zh: "工作流调度" },
  "status.rateLimits": { en: "Rate Limits", zh: "速率限制" },

  // ── API docs ──
  "api.accent": { en: "API", zh: "API" },
  "api.suffix": { en: "Documentation", zh: "文档" },
  "api.subtitle": { en: "Access all radar data via public JSON endpoints", zh: "通过公开 JSON 端点访问所有雷达数据" },
  "api.baseUrl": { en: "Base URL", zh: "基础 URL" },
  "api.badges": { en: "README Badges", zh: "README 徽章" },
  "api.endpoints": { en: "Endpoints", zh: "端点" },
  "api.usageExample": { en: "Usage Example", zh: "使用示例" },
  "api.colMethod": { en: "Method", zh: "方法" },
  "api.colEndpoint": { en: "Endpoint", zh: "端点" },
  "api.colDescription": { en: "Description", zh: "描述" },
  "api.scoreBadge": { en: "Score badge", zh: "评分徽章" },
  "api.velocityBadge": { en: "Velocity badge", zh: "速度徽章" },
  "api.availableBadges": { en: "Available badges", zh: "可用徽章" },
  "api.badgeCol": { en: "Badge", zh: "徽章" },
  "api.badgeShows": { en: "Shows", zh: "展示内容" },
  "api.badgeIntro": { en: "Show your project's live Radar Score in your README — it updates automatically every day. Replace OWNER__REPO with your GitHub owner and repo joined by two underscores (e.g. BerriAI__litellm).", zh: "在你的 README 中展示项目的实时雷达评分 — 每日自动更新。将 OWNER__REPO 替换为你的 GitHub 所有者与仓库名（用两个下划线连接，例如 BerriAI__litellm）。" },
  "api.badgeScoreDesc": { en: "Live radar score, colored by tier", zh: "实时雷达评分，按层级着色" },
  "api.badgeVelocityDesc": { en: "7-day star velocity", zh: "7 天 star 速度" },
  "api.badgeStarsDesc": { en: "Total star count", zh: "总 star 数" },
  "api.badgeFooter": { en: "Ranked at the top of your category? Your score badge is a great way to show it off.", zh: "在你所属分类中名列前茅？评分徽章是展示实力的好方式。" },

  // ── Extra UI units / trend words ──
  "unit.stars": { en: "stars", zh: "星标" },
  "unit.projects": { en: "projects", zh: "个项目" },
  "unit.nProjects": { en: "{n} projects", zh: "{n} 个项目" },
  "trend.rising": { en: "rising", zh: "上升" },
  "trend.stable": { en: "stable", zh: "平稳" },
  "trend.declining": { en: "declining", zh: "回落" },

  // ── Project detail dynamic copy ──
  "proj.origNote": { en: "Original description (English)", zh: "原文描述（英文）" },
  "proj.topPercentile": { en: "Top {n}% globally", zh: "全球前 {n}%" },
  "proj.maturityLabel": { en: "Maturity: {v}", zh: "成熟度：{v}" },
  "proj.lastPushDays": { en: "Last push {n}d ago", zh: "最近推送于 {n} 天前" },
  "proj.stars7dBadge": { en: "+{n} stars / 7d", zh: "7 天新增 +{n} star" },
  "proj.stars30dBadge": { en: "+{n} stars / 30d", zh: "30 天新增 +{n} star" },
  "proj.trendSignal": { en: "Trend signal:", zh: "趋势信号：" },
  "proj.stars7dLabel": { en: "7-Day Stars", zh: "7 天新增 Star" },
  "proj.stars30dLabel": { en: "30-Day Stars", zh: "30 天新增 Star" },
  "proj.accelLabel": { en: "Acceleration", zh: "加速度" },
  "proj.languageLabel": { en: "Language", zh: "语言" },
  "proj.vstory.v70": {
    en: "Exceptional momentum — gaining stars far faster than almost everything else tracked.",
    zh: "动量极为强劲 — star 增长速度远超几乎所有在跟踪的项目。",
  },
  "proj.vstory.v50": {
    en: "Strong momentum — adoption is accelerating week over week.",
    zh: "动量强劲 — 采用度逐周加速增长。",
  },
  "proj.vstory.v35": {
    en: "Steady growth — consistently collecting stars and contributors.",
    zh: "稳定增长 — 持续积累 star 与贡献者。",
  },
  "proj.vstory.v15": {
    en: "Modest but positive momentum.",
    zh: "动量温和但为正向。",
  },
  "proj.vstory.v0": {
    en: "Momentum is cooling relative to the rest of the index.",
    zh: "相对指数中其他项目，动量正在放缓。",
  },
  "proj.subcatWith": { en: " · {v}", zh: "·{v}" },

  // ── "Why it ranks" explanation segments (rebuilt client-side from signals,
  //    mirroring radar/analysis/why_trending.py thresholds — no MT, bilingual) ──
  "why.rapid": {
    en: "Rapidly gaining stars — {n} new stars in the last 7 days ({x}x the usual pace)",
    zh: "星标飞速增长 — 近 7 天新增 {n} 个 star（为平时速度的 {x} 倍）",
  },
  "why.strong": {
    en: "Strong momentum with {n} new stars this week",
    zh: "本周新增 {n} 个 star，动量强劲",
  },
  "why.steady": {
    en: "Steady growth with {n} new stars this week",
    zh: "本周新增 {n} 个 star，稳步增长",
  },
  "why.fastest": {
    en: "Among the fastest-growing projects in its category",
    zh: "所属分类中增长最快的项目之一",
  },
  "why.aboveAvg": {
    en: "Above-average growth velocity",
    zh: "增长速度快于平均水平",
  },
  "why.forks": {
    en: "High developer adoption with {n} new forks this week",
    zh: "开发者采用度高，本周新增 {n} 个 fork",
  },
  "why.wellMaintained": {
    en: "Well-maintained with active development",
    zh: "维护良好，开发活跃",
  },
  "why.declining": {
    en: "⚠️ Declining health metrics — may need attention",
    zh: "⚠️ 健康度指标下滑 — 值得关注",
  },
  "why.starSpike": {
    en: "🚨 Unusual star activity detected — possible viral moment",
    zh: "🚨 检测到异常的 star 增长活动 — 可能正在病毒式传播",
  },
  "why.activeIn": {
    en: "Active in the {cat} category",
    zh: "活跃于{cat}领域",
  },
  "why.emerging": {
    en: "New and emerging project",
    zh: "新兴项目",
  },
  "why.mature": {
    en: "Established project with proven track record",
    zh: "成熟项目，履历可靠",
  },
  "why.popular": {
    en: "Popular project with significant community interest",
    zh: "广受欢迎，社区关注度高",
  },
  "why.growing": {
    en: "Growing project gaining traction",
    zh: "持续增长、逐渐获得关注的项目",
  },
  "why.positive": {
    en: "Project showing positive momentum",
    zh: "展现出积极动量的项目",
  },
  "why.sep": { en: ". ", zh: "；" },
  "why.end": { en: ".", zh: "。" },

  // ── Status page detailed copy ──
  "status.wfDiscover": { en: "Discover", zh: "发现" },
  "status.wfDiscoverDesc": { en: "Searches GitHub for new AI projects across 11 categories.", zh: "在 11 个分类中搜索 GitHub 上的新 AI 项目。" },
  "status.wfProcess": { en: "Process", zh: "处理" },
  "status.wfProcessDesc": { en: "Snapshots and scores repos by tier (T1 daily → T4 monthly).", zh: "按层级为仓库生成快照并评分（T1 每日 → T4 每月）。" },
  "status.wfDeploy": { en: "Deploy", zh: "部署" },
  "status.wfDeployDesc": { en: "Builds Astro site and deploys to GitHub Pages.", zh: "构建 Astro 站点并部署到 GitHub Pages。" },
  "status.wfWeekly": { en: "Weekly Report", zh: "每周报告" },
  "status.wfWeeklyDesc": { en: "Generates intelligence report, social drafts, and RSS feed.", zh: "生成情报报告、社交草稿与 RSS 订阅。" },
  "status.rows": { en: "rows", zh: "行" },
  "status.lastSnapshotL": { en: "Last snapshot:", zh: "最近快照：" },
  "status.lastScore": { en: "Last score:", zh: "最近评分：" },
  "status.lastDiscovery": { en: "Last discovery:", zh: "最近发现：" },
  "status.snapshotted": { en: "{a} / {b} repos snapshotted", zh: "{a} / {b} 个仓库已快照" },
  "status.scored": { en: "{a} / {b} repos scored", zh: "{a} / {b} 个仓库已评分" },
  "status.processed": { en: "Processed: {a} / {b}", zh: "已处理：{a} / {b}" },
  "status.lastRun": { en: "Last run:", zh: "最近运行：" },
  "status.chk.freshness": { en: "Data Freshness", zh: "数据新鲜度" },
  "status.chk.snapshot": { en: "Snapshot Coverage", zh: "快照覆盖" },
  "status.chk.scoring": { en: "Scoring Coverage", zh: "评分覆盖" },
  "status.chk.category": { en: "Category Coverage", zh: "分类覆盖" },
  "status.chk.database": { en: "Database Health", zh: "数据库健康" },
  "status.chk.processing": { en: "Processing Stats", zh: "处理统计" },
  "status.overall.healthy": { en: "healthy", zh: "健康" },
  "status.overall.warning": { en: "warning", zh: "警告" },
  "status.overall.critical": { en: "critical", zh: "严重" },
  "status.overall.unknown": { en: "unknown", zh: "未知" },
  "status.time.never": { en: "Never", zh: "从未" },
  "status.time.justNow": { en: "Just now", zh: "刚刚" },
  "status.time.mins": { en: "{n}m ago", zh: "{n} 分钟前" },
  "status.time.hrs": { en: "{n}h ago", zh: "{n} 小时前" },
  "status.time.days": { en: "{n}d ago", zh: "{n} 天前" },
  "status.wfDiscoverWhen": { en: "2x daily — 02:00, 14:00 UTC", zh: "每日 2 次 — 02:00、14:00 UTC" },
  "status.wfDiscoverCalls": { en: "~120 GraphQL calls per run", zh: "每次运行约 120 次 GraphQL 调用" },
  "status.wfProcessWhen": { en: "4x daily — 04:00, 10:00, 16:00, 22:00 UTC", zh: "每日 4 次 — 04:00、10:00、16:00、22:00 UTC" },
  "status.wfProcessCalls": { en: "~350 GraphQL calls per run", zh: "每次运行约 350 次 GraphQL 调用" },
  "status.wfDeployWhen": { en: "On push to main — automatic", zh: "推送到 main 时 — 自动" },
  "status.wfDeployCalls": { en: "No API calls (build only)", zh: "无 API 调用（仅构建）" },
  "status.wfWeeklyWhen": { en: "Monday 08:00 UTC", zh: "每周一 08:00 UTC" },
  "status.wfWeeklyCalls": { en: "~50 GraphQL calls", zh: "约 50 次 GraphQL 调用" },
  "status.rlBudget": { en: "Budget per hour", zh: "每小时预算" },
  "status.rlBudgetSub": { en: "GITHUB_TOKEN", zh: "GITHUB_TOKEN" },
  "status.rlSafety": { en: "Safety threshold", zh: "安全阈值" },
  "status.rlSafetySub": { en: "800 pts max per run", zh: "每次运行最多 800 点" },
  "status.rlDaily": { en: "Daily usage", zh: "每日用量" },
  "status.rlDailySub": { en: "Across all workflows", zh: "所有工作流合计" },
  "status.perRun": { en: "per run", zh: "每次运行" },
};

/** Resolve a dictionary entry for a language. Returns the key if missing. */
export function t(key: string, lang: Lang): string {
  const entry = dict[key];
  if (!entry) return key;
  return entry[lang] ?? entry.en;
}

/** Fill `{placeholders}` in a translated template. */
export function tf(key: string, lang: Lang, vars: Record<string, string | number>): string {
  let s = t(key, lang);
  for (const [k, v] of Object.entries(vars)) s = s.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
  return s;
}

/** Determine the active language from storage or browser preference. */
export function getLang(): Lang {
  if (typeof document === "undefined") return "en";
  try {
    const stored = document.documentElement.getAttribute("data-lang");
    if (stored === "en" || stored === "zh") return stored;
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (saved === "en" || saved === "zh") return saved;
  } catch {
    /* localStorage unavailable */
  }
  const nav = typeof navigator !== "undefined" ? navigator.language || "" : "";
  return nav.toLowerCase().startsWith("zh") ? "zh" : "en";
}

/** Apply translations to every [data-i18n] node under `root`. */
export function applyI18n(root: ParentNode, lang: Lang): void {
  root.querySelectorAll<HTMLElement>("[data-i18n]").forEach((el) => {
    const vars = parseVars(el.dataset.i18nVars);
    if (vars) applyVarMaps(vars, parseVars(el.dataset.i18nMap), lang);
    el.textContent = vars ? tf(el.dataset.i18n!, lang, vars) : t(el.dataset.i18n!, lang);
  });
  root.querySelectorAll<HTMLElement>("[data-i18n-html]").forEach((el) => {
    const vars = parseVars(el.dataset.i18nVars);
    el.innerHTML = vars ? tf(el.dataset.i18nHtml!, lang, vars) : t(el.dataset.i18nHtml!, lang);
  });
  root.querySelectorAll<HTMLElement>("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder!, lang));
  });
  root.querySelectorAll<HTMLElement>("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria!, lang));
  });
  // Category labels: English source lives in the attribute, so toggling back
  // to English restores it exactly.
  root.querySelectorAll<HTMLElement>("[data-i18n-cat]").forEach((el) => {
    const en = el.dataset.i18nCat!;
    el.textContent = lang === "zh" ? catMap[en] || en : en;
  });
  // Machine-translated project descriptions (build-time cache). Falls back to
  // the English source when no translation is available.
  root.querySelectorAll<HTMLElement>("[data-desc-en]").forEach((el) => {
    const en = el.getAttribute("data-desc-en") || "";
    const zh = el.getAttribute("data-desc-zh") || "";
    el.textContent = lang === "zh" && zh ? zh : en;
  });
  // Reflect state so server-less toggles survive re-application.
  (root as Document).documentElement?.setAttribute?.("data-lang", lang);
}

/** Persist + apply a language across the document, then notify listeners. */
export function setLang(lang: Lang): void {
  if (typeof document === "undefined") return;
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    /* ignore */
  }
  document.documentElement.setAttribute("data-lang", lang);
  document.documentElement.setAttribute("lang", lang === "zh" ? "zh-CN" : "en");
  applyI18n(document, lang);
  document.dispatchEvent(new CustomEvent("radar:lang", { detail: { lang } }));
}

export function toggleLang(): Lang {
  const next: Lang = getLang() === "en" ? "zh" : "en";
  setLang(next);
  return next;
}

/** Parse a JSON `data-i18n-vars` attribute into a substitution map. */
function parseVars(raw: string | undefined): Record<string, string | number> | undefined {
  if (!raw) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}

/** Localize flagged dynamic vars (category/maturity/sub-category) in place.
 *  Only mutates for `zh`; English keeps the source value. Case-insensitive so
 *  free-form DB casing still maps; unknown values stay as-is (proper nouns). */
function applyVarMaps(
  vars: Record<string, string | number>,
  spec: Record<string, string | number> | undefined,
  lang: Lang,
): void {
  if (!spec || lang !== "zh") return;
  for (const [name, kind] of Object.entries(spec)) {
    const map = VAR_MAPS[String(kind)];
    const v = vars[name];
    if (!map || v == null) continue;
    const s = String(v);
    vars[name] = map[s] || map[s.toLowerCase()] || s;
  }
}
