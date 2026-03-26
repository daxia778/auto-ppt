"""
主入口
NotebookLM PPT Generator 命令行应用。
"""
import asyncio
import argparse
import sys
import yaml
import os
import time

from src.auth import AuthManager
from src.notebook import NotebookManager
from src.parser import ContentParser
from src.generator import PPTGenerator

def load_config(config_path="config.yaml"):
    """加载 YAML 配置"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: 配置文件 {config_path} 未找到！")
        sys.exit(1)

def get_text_content(args) -> str:
    """根据参数获取素材内容"""
    if args.source_text:
        return args.source_text
    elif args.source_file:
        try:
            with open(args.source_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error: 无法读取素材文件: {str(e)}")
            sys.exit(1)
    else:
        # 如果没有提供素材，给一个简短的提示词，让 AI 根据常识生成
        return "请利用你的知识库，帮我总结相关内容。"

async def run_ppt_generation(args):
    """端到端的 PPT 生成流程"""
    config = load_config()
    
    auth_manager = AuthManager(config)
    context = None
    
    try:
        print("\n" + "="*50)
        print("  >>> 启动 NotebookLM PPT Generator")
        print("="*50 + "\n")
        
        start_time = time.time()
        
        # 1. 启动浏览器 & 确保登录
        context = await auth_manager.launch_browser()
        page = context.pages[0] if context.pages else await context.new_page()
        
        logged_in = await auth_manager.ensure_logged_in(page)
        if not logged_in:
             print("[FAIL] 登录失败，流程终止。")
             return

        # 2. NotebookLM 自动化
        notebook_mgr = NotebookManager(page, config)
        
        print(f"\n[任务] 主题: {args.topic}")
        print(f"[任务] 页数: {args.pages}")
        
        await notebook_mgr.create_new_notebook()
        
        # 获取素材并添加
        source_content = get_text_content(args)
        if source_content and len(source_content) > 10:
             await notebook_mgr.add_source(source_content)
        
        # 构造 Prompt
        prompt_template = config.get("prompts", {}).get("generate_outline", "")
        if not prompt_template:
            prompt_template = "帮我生成关于【{topic}】的 {pages} 页PPT大纲"
            
        prompt = prompt_template.format(topic=args.topic, pages=args.pages)
        
        # 发送并获取回复
        response_text = await notebook_mgr.send_prompt_and_get_response(prompt)
        
        if not response_text:
             print("\n[FAIL] 未能获取到 AI 生成的内容")
             return
             
        if args.use_studio:
            # 流程 A: 使用官方 Studio 面板生成演示文稿
            print("\n[模式] 启用官方 Studio 生成模式")
            
            studio_config = config.get("studio", {})
            max_retries = studio_config.get("retry_count", 1) + 1
            output_dir = os.path.abspath(config.get("ppt", {}).get("output_dir", "./output"))
            
            success = False
            for attempt in range(1, max_retries + 1):
                try:
                    if attempt > 1:
                        print(f"\n[重试] 第 {attempt}/{max_retries} 次尝试生成...")
                        # 等待一小段时间再重试
                        await page.wait_for_timeout(3000)
                        
                    await notebook_mgr.generate_studio_presentation()
                    ready = await notebook_mgr.wait_for_presentation_ready()
                    
                    if ready:
                        output_path = await notebook_mgr.download_presentation(dest_dir=output_dir)
                        if os.path.exists(output_path):
                            file_size = os.path.getsize(output_path) / (1024 * 1024)
                            print(f"[验证] 文件成功下载并保存! 大小: {file_size:.2f} MB")
                            success = True
                            break
                        else:
                            print(f"[错误] 文件声称已下载，但在路径未找到: {output_path}")
                    else:
                        print(f"[警告] 第 {attempt} 次生成等待超时或失败。")
                except Exception as e:
                    print(f"[警告] 第 {attempt} 次尝试中发生异常: {str(e)}")
            
            if not success:
                print("\n[FAIL] 演示文稿生成失败 (已达到最大重试次数)")
                return
                
        else:
            # 流程 B: 后备模式 - 解析聊天文本并使用 python-pptx 生成
            print("\n[模式] 启用本地解析生成模式 (Fallback)")
            # 3. 解析为结构化数据
            parser = ContentParser()
            slides_data = parser.parse_markdown(response_text)
            
            if not slides_data:
                 print("\n[FAIL] 解析 Markdown 失败，没有得到有效的幻灯片数据")
                 return
                 
            # 4. 生成 PPT
            generator = PPTGenerator(config)
            output_path = generator.generate(slides_data, title_text=args.topic)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*50)
        print("  [DONE] 流程完成!")
        print(f"  [STAT] 总耗时: {duration:.1f} 秒")
        print(f"  [FILE] 输出文件: {output_path}")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n[ERROR] 发生严重错误: {str(e)}")
    
    finally:
        # 确保浏览器关闭
        await auth_manager.close()

async def run_login_only():
    config = load_config()
    auth_manager = AuthManager(config)
    await auth_manager.login_only()

async def run_parse_test(args):
    """纯离线测试解析逻辑"""
    print("\n--- 运行离线解析测试 ---")
    
    # 模拟一个 notebooklm 的回复
    test_input = """
## 第1页
**标题**: {topic} - 封面
**要点**:
- 快速入门指南
- 从零到一构建你的应用
**备注**: 欢迎大家参加本次分享。

## 第2页
**标题**: 核心功能概览
**要点**:
- 功能 A 介绍
- 功能 B 的技术栈
- 未来规划地图
**备注**: 这部分重点讲述我们的技术优势。
    """.format(topic=args.topic)
    
    parser = ContentParser()
    slides = parser.parse_markdown(test_input)
    
    import json
    print("\n[结构化数据输出]")
    print(json.dumps(slides, indent=2, ensure_ascii=False))
    
    config = load_config()
    generator = PPTGenerator(config)
    generator.generate(slides, f"{args.topic}_Test")
    
def main():
    parser = argparse.ArgumentParser(description="NotebookLM PPT Generator")
    
    # 基本参数
    parser.add_argument("--topic", type=str, default="测试生成PPT", help="PPT 的主题/标题")
    parser.add_argument("--pages", type=int, default=5, help="希望生成的 PPT 页数")
    
    # 素材参数
    parser.add_argument("--source-text", type=str, help="直接提供一段文本作为素材")
    parser.add_argument("--source-file", type=str, help="从本地文件(如.txt)读取素材")
    
    # 特殊模式
    parser.add_argument("--login-only", action="store_true", help="仅运行登录流程(首次使用)")
    parser.add_argument("--parse-test", action="store_true", help="本地离线测试解析和生成流程，不需浏览器")
    parser.add_argument("--use-studio", action=argparse.BooleanOptionalAction, default=True, help="使用 Studio 面板直接生成 PPTX (默认开启)")
    
    args = parser.parse_args()
    
    if args.login_only:
         asyncio.run(run_login_only())
    elif args.parse_test:
         asyncio.run(run_parse_test(args))
    else:
         asyncio.run(run_ppt_generation(args))

if __name__ == "__main__":
    main()
