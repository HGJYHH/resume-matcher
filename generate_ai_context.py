import os

# ================= 配置区 =================
# 1. 指定要读取的包或目录（相对于项目根目录）
# 例如前端项目只想看页面：'pages'，只想看组件：'components'
# 如果要读取全量项目，请保持为 '.'
TARGET_PACKAGE = '.' 

# 2. 项目根路径（通常脚本就在根目录，保持 '.'）
PROJECT_ROOT = '.'

# 3. 输出文件名
OUTPUT_FILE = 'ai_project_context_admin.md'

# 4. 忽略的目录
IGNORE_DIRS = {
    '.git', '.idea', '.vscode', 'node_modules',
    'target', 'build', 'dist', '__pycache__','.venv'
}

# 5. 忽略的文件后缀
IGNORE_EXTS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.mp4',
    '.pdf', '.zip', '.tar', '.gz', '.class', '.jar',
    '.exe', '.dll', 'package-lock.json', '.DS_Store',
    '.env'
    # --- 手动选择区：如果不需要 AI 读取 yml，请取消下面两行的注释 ---
    # '.yml',
    # '.yaml',
}
# ==========================================

def is_ignored(path):
    for part in path.split(os.sep):
        if part in IGNORE_DIRS:
            return True
    _, ext = os.path.splitext(path)
    if ext.lower() in IGNORE_EXTS:
        return True
    filename = os.path.basename(path)
    if filename in ['generate_ai_context.py', OUTPUT_FILE]:
        return True
    return False

def generate_project_tree(scan_dir):
    tree_str = f"## 项目目录结构 (目标范围: {scan_dir})\n```text\n"
    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        level = root.replace(scan_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        tree_str += f"{indent}{os.path.basename(root)}/\n"
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if not is_ignored(os.path.join(root, f)):
                tree_str += f"{subindent}{f}\n"
    tree_str += "```\n\n"
    return tree_str

def get_language(filename):
    ext = os.path.splitext(filename)[1].lower()
    mapping = {
        '.java': 'java', '.js': 'javascript', '.ts': 'typescript',
        '.vue': 'vue', '.xml': 'xml', '.yml': 'yaml', '.yaml': 'yaml',
        '.sql': 'sql', '.html': 'html', '.css': 'css', '.py': 'python',
        '.sh': 'bash', '.md': 'markdown', '.json': 'json', '.properties': 'properties'
    }
    return mapping.get(ext, 'text')

def generate_file_contents(scan_dir):
    content_str = "## 每一个文件的代码内容\n\n"
    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            file_path = os.path.join(root, f)
            if not is_ignored(file_path):
                # 这里显示相对于项目根目录的路径，方便 AI 定位
                rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                content_str += f"### 文件路径: `{rel_path}`\n"
                content_str += f"```{get_language(f)}\n"
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content_str += file.read() + "\n"
                except Exception as e:
                    content_str += f"// 读取失败: {e}\n"
                content_str += "```\n\n"
    return content_str

if __name__ == '__main__':
    # 组合成完整的扫描路径
    target_path = os.path.join(PROJECT_ROOT, TARGET_PACKAGE)
    
    if not os.path.exists(target_path):
        print(f"错误: 找不到路径 {target_path}")
    else:
        print(f"正在扫描目标范围: {target_path}")
        tree_output = generate_project_tree(target_path)
        contents_output = generate_file_contents(target_path)

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("# 项目代码上下文\n\n")
            f.write(f"> 扫描范围：{TARGET_PACKAGE}\n\n")
            f.write(tree_output)
            f.write(contents_output)

        print(f"执行完毕！已生成: {os.path.abspath(OUTPUT_FILE)}")