import os
import sys
import click
import traceback

# 【关键路径修复】确保能引用当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 动态导入 (防止循环引用)
try:
    from func_ import load_conf
    from inner import run_inner
    from excircle import run_excircle
    from circos import run_circos
except ImportError as e:
    print(f"Import Error in run.py: {e}")
    # 尝试相对导入
    try:
        from .func_ import load_conf
        from .inner import run_inner
        from .excircle import run_excircle
        from .circos import run_circos
    except:
        traceback.print_exc()

@click.group()
def main():
    """GF-Circos Drawing Tools"""
    pass

@main.command('excircle')
@click.option('-c', '--conf', required=True, help='Config file path')
def excircle_cmd(conf):
    try:
        if os.path.exists(conf):
            options = load_conf(conf, 'excircle')
            # 实例化并运行
            app = run_excircle(options)
            # 注意：excircle.py 的代码里逻辑是在 __init__ 执行的，还是有 run 方法？
            # 根据你给的代码，绘图逻辑全在 __init__ 里。
            # 如果有 run() 方法，请取消下面注释：
            # app.run() 
            print("Excircle plot finished.")
        else:
            print(f"Config file not found: {conf}")
    except Exception:
        traceback.print_exc()
        sys.exit(1)

@main.command('inner')
@click.option('-c', '--conf', required=True, help='Config file path')
def inner_cmd(conf):
    try:
        if os.path.exists(conf):
            options = load_conf(conf, 'inner')
            run_inner(options)
            print("Inner plot finished.")
        else:
            print(f"File not found: {conf}")
    except Exception:
        traceback.print_exc()
        sys.exit(1)

@main.command('circos')
@click.option('-c', '--conf', required=True, help='Config file path')
@click.option('--format', default='processed')
def circos_cmd(conf, format):
    try:
        if os.path.exists(conf):
            options = load_conf(conf, 'circos')
            app = run_circos(options, format)
            app.run()
            print("Circos plot finished.")
        else:
            print(f"File not found: {conf}")
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()