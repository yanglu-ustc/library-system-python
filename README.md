# 图书管理系统（基于 openGauss）

一个基于 **openGauss 数据库** 和 **Flask 框架** 实现的简单图书管理系统，支持图书入库、借阅、归还、损坏标记、批量淘汰、高级检索及统计等功能。

## 📌 功能亮点

- 用户登录（区分普通用户与管理员）
- 图书实例管理（添加、批量副本）
- 借阅与归还（支持标记图书是否损坏）
- 管理员专属功能：
  - 标记/批量淘汰损坏图书
  - 查看所有借阅记录
  - 多维度统计（区域、作者、年份、借阅状态等）
- 高级检索：支持多条件组合查询 + 三级排序

## 🛠 技术栈

- **后端**：Python + Flask
- **数据库**：openGauss（通过 `psycopg2` 连接）
- **前端**：原生 HTML + Flask 模板渲染
- **部署**：Docker 容器化运行 openGauss

## 📁 项目结构

```
library-system/
├── ui.py                 # Flask 主应用
├── library_ui.py         # 业务逻辑封装（LibrarySQL 类）
├── sql.py                # 数据库连接配置
├── library_start.sql     # 初始化数据库脚本
├── library_end.sql       # 清理脚本
├── requirements.txt      # Python 依赖
└── templates/            # HTML 页面模板
```

## ▶️ 快速启动

1. 启动 openGauss（推荐 Docker）
2. 设置环境变量（`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`）
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 初始化数据库（执行 `library_start.sql`）
5. 运行应用：
   ```bash
   python ui.py
   ```

你也可以在配置好环境之后直接执行`run.bash`或`run.ps1`

---

如有兴趣，可参见 report.pdf 文件

欢迎使用！如有问题，请联系作者：luyang2008@mail.ustc.edu.cn
