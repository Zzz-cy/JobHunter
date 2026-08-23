"""
启动脚本 - 同时启动FastAPI后端和Vue前端开发服务器

使用方法:
    python start_frontend.py

然后打开浏览器访问: http://localhost:5173
"""
import subprocess
import sys
import os
import time
import webbrowser
import socket
import threading

# 修复Windows终端GBK编码不支持emoji的问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ========== 统一端口配置 ==========
BACKEND_PORT = 5173    # FastAPI 后端端口
FRONTEND_PORT = 3000   # Vite 前端开发服务器端口


def check_port(port, host='localhost'):
    """检查端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def check_http_ready(url, timeout=3):
    """通过HTTP请求检查服务是否真正就绪（比端口检测更可靠）"""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_port(port, host='localhost', timeout=30):
    """等待端口就绪"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_port(port, host):
            return True
        time.sleep(0.5)
    return False


def wait_for_http(url, timeout=120, interval=1):
    """等待HTTP服务真正就绪（应用已加载完成）"""
    start_time = time.time()
    last_log = 0
    while time.time() - start_time < timeout:
        if check_http_ready(url):
            return True
        # 每10秒打印一次等待状态，避免用户以为卡死
        elapsed = int(time.time() - start_time)
        if elapsed > 0 and elapsed % 10 == 0 and elapsed != last_log:
            last_log = elapsed
            print(f"   ...已等待 {elapsed}s，服务仍在启动中")
        time.sleep(interval)
    return False


def read_output(proc, prefix):
    """读取进程输出并打印"""
    try:
        for line in proc.stdout:
            if line:
                print(f"[{prefix}] {line.rstrip()}")
    except Exception:
        pass


def start_backend():
    """启动FastAPI后端"""
    print(f"🚀 启动 FastAPI 后端服务...")
    print(f"   地址: http://localhost:{BACKEND_PORT}")
    print(f"   API文档: http://localhost:{BACKEND_PORT}/docs")
    print()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "api.main:app",
                "--host", "0.0.0.0",
                "--port", str(BACKEND_PORT),
                "--reload"
            ],
            cwd=base_dir,
            stdout=None,   # 直接输出到终端，避免PIPE缓冲区满导致进程阻塞
            stderr=None,
        )

        return proc
    except Exception as e:
        print(f"❌ 启动后端失败: {e}")
        return None


def start_frontend():
    """启动Vue前端开发服务器（Vite）"""
    print(f"🌐 启动 Vue 前端开发服务（Vite）...")
    print(f"   地址: http://localhost:{FRONTEND_PORT}")
    print()

    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

    # 检查node_modules是否存在
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("📦 正在安装前端依赖（npm install）...")
        try:
            subprocess.run(
                "npm install",
                cwd=frontend_dir,
                check=True,
                capture_output=True,
                text=True,
                shell=True,
            )
            print("✅ 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ npm install 失败: {e.stderr}")
            return None

    try:
        # 使用本地node_modules中的vite，避免npx远程下载最新版导致超时
        shell_mode = sys.platform == "win32"
        if shell_mode:
            # Windows下shell=True执行，使用.cmd扩展名更可靠
            vite_bin = os.path.join(frontend_dir, "node_modules", ".bin", "vite.cmd")
            cmd = f'"{vite_bin}" --host --port {FRONTEND_PORT}'
        else:
            vite_bin = os.path.join(frontend_dir, "node_modules", ".bin", "vite")
            cmd = [vite_bin, "--host", "--port", str(FRONTEND_PORT)]

        proc = subprocess.Popen(
            cmd,
            cwd=frontend_dir,
            stdout=None,   # 直接输出到终端，避免PIPE缓冲区满导致进程阻塞
            stderr=None,
            shell=shell_mode,
        )

        return proc
    except Exception as e:
        print(f"❌ 启动前端失败: {e}")
        return None


def main():
    print("=" * 60)
    print("  岗能智绘 - Agent智能问答测试平台")
    print("=" * 60)
    print()

    backend_proc = None
    frontend_proc = None

    try:
        if check_port(BACKEND_PORT):
            print(f"⚠️  端口 {BACKEND_PORT} 已被占用，后端可能已在运行")

        if check_port(FRONTEND_PORT):
            print(f"⚠️  端口 {FRONTEND_PORT} 已被占用，前端可能已在运行")

        # 启动后端
        print("📡 正在启动后端服务...")
        backend_proc = start_backend()
        if backend_proc is None:
            print("❌ 后端启动失败")
            return

        print("⏳ 等待后端服务就绪...")
        if wait_for_http(f"http://localhost:{BACKEND_PORT}/health", timeout=120):
            print("✅ 后端服务已就绪!")
        else:
            print("❌ 后端服务启动超时")
            return

        # 启动前端
        print("📡 正在启动前端服务...")
        frontend_proc = start_frontend()
        if frontend_proc is None:
            print("❌ 前端启动失败")
            return

        print("⏳ 等待前端服务就绪...")
        if wait_for_http(f"http://localhost:{FRONTEND_PORT}", timeout=120):
            print("✅ 前端服务已就绪!")
        else:
            print("❌ 前端服务启动超时")
            return

        print("🎉 服务启动完成!")
        print()
        print("访问地址:")
        print(f"  🌐 前端页面:    http://localhost:{FRONTEND_PORT}")
        print(f"  📚 API文档:     http://localhost:{BACKEND_PORT}/docs")
        print(f"  🔍 健康检查:    http://localhost:{BACKEND_PORT}/health")
        print("  🗄️  Neo4j管理:  http://localhost:7474/browser/")
        print()
        print("按 Ctrl+C 停止服务")

        try:
            webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
        except:
            pass

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    finally:
        print()
        print("👋 正在停止服务...")
        if frontend_proc:
            frontend_proc.terminate()
            print("   前端服务已停止")
        if backend_proc:
            backend_proc.terminate()
            print("   后端服务已停止")
        print("👋 服务已停止")


if __name__ == "__main__":
    main()
