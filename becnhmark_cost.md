# 📄 Performance and Cost Benchmarks

In this analysis, we evaluated how two major AI reviewers — **GPT-4o-mini** and **Grok-3-mini-beta** — handle intentionally injected code issues in two different codebases:

- **Java** (`PurgeManager`)
- **TypeScript** (`main.ts` server initialization)

The objective was to simulate realistic coding errors, including concurrency bugs, null-pointer risks, async handling mistakes, and performance bottlenecks, and measure how different AI review tools perform.

---

## 🛠 Introduced Bugs with Abstract Examples

| Language | Bug Description | Abstract Code Example |
|:---------|:----------------|:----------------------|
| **Java** | 1. **Removed variable initialization** | ```java private ScheduledExecutorService executor; public void schedule() { executor.schedule(...); } // executor might be null! ``` |
|           | 2. **Created unsafe API that modifies input** | ```java public void clearList(List<String> items) { items.clear(); } ``` |
|           | 3. **Removed try-catch blocks** | ```java dbClient.queryData(); // throws exception but no try-catch around it ``` |
|           | 4. **Removed lock protection** | ```java if (executor == null) { executor = Executors.newSingleThreadScheduledExecutor(); } executor.schedule(...); // race condition possible ``` |
|           | 5. **Performance/security issue in logging** | ```java logger.info("User data: {}", fullUserDataObject); // might log sensitive information or huge payloads ``` |
| **TypeScript** | 1. **Removed fallback (`?? ''`) for undefined** | ```ts const clusterUser = config.get('user'); // clusterUser might be undefined later ``` |
|              | 2. **Syntax error introduced** | ```ts const user = { name: "John"  // missing closing bracket ``` |
|              | 3. **Removed `await` causing async issues** | ```ts const connection = db.connect(); // missing await; connection is Promise ``` |
|              | 4. **Logged full object without limitation** | ```ts console.log("Loaded context: ", JSON.stringify(runtimeContext)); // could be huge object ``` |
|              | 5. **Silenced possible exceptions** | ```ts someAsyncFunction().catch(() => {}); // errors ignored without logging ``` |

---

## 🧪 AI Code Review Results

| Tool | Language | Prompt Style | Issues Caught | Issues Missed | Comment |
|:-----|:---------|:-------------|:--------------|:--------------|:--------|
| **GPT-4o-mini** | Java | Simple | 2, 3 | 1, 4, 5 missed | Skipped context-based and performance issues |
| **GPT-4o-mini** | Java | Complex | All caught | - |
| **GPT-4o-mini** | TS | Simple | All caught | - |
| **GPT-4o-mini** | TS | Complex | All caught | - |
| **Grok-3-mini-beta** | Java | Simple | 2, 3 | 1, 4, 5 missed | Similar to GPT behavior |
| **Grok-3-mini-beta** | Java | Complex | All caught | - |
| **Grok-3-mini-beta** | TS | Simple | All caught | - |
| **Grok-3-mini-beta** | TS | Complex | All caught | - |

---

## 📈 Token and Cost Comparison

| Metric | GPT-4o-mini | Grok-3-mini-beta |
|:-------|:------------|:-----------------|
| **Input Tokens** | ~120k | ~90k |
| **Output Tokens** | ~18k | ~23k |
| **Total Tokens** | ~138k | ~113k |
| **Cost** | ~$0.03 | ~$0.04 |

- price for **Grok-3-mini-beta** is comparable to GPT-4o-mini.
- **Grok-3-mini-beta** generated **more detailed actionable fixes**, whereas **GPT-4o-mini** provided **more general section-based suggestions**.

---

## 🧠 Behavior Observations

| Category | GPT-4o-mini | Grok-3-mini-beta |
|:---------|:------------|:----------------|
| **Instruction Clarity** | General advice | Specific, actionable fixes |
| **Context Sensitivity** | Needs full context to catch all | Same |
| **Performance/Concurrency Awareness** | Only with deep prompts | Only with deep prompts |
| **Async Error Detection** | Needs explicit async checking | Needs explicit async checking |
| **Silenced Errors Detection** | Good | Good |

---

# 📋 End of Report
