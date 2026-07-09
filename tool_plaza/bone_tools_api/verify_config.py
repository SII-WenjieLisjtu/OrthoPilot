#!/usr/bin/env python3
"""环境配置验证脚本"""
import os
from pathlib import Path
from dotenv import load_dotenv


def verify_environment():
    """验证环境配置"""
    print("=" * 60)
    print("环境配置验证")
    print("=" * 60)

    # 检查配置文件
    env_file = Path(".env")
    env_example = Path(".env.example")
    openai_file = Path(".openai")

    print("\n配置文件检查:")
    print(f"  ✓ .env.example: {'存在' if env_example.exists() else '不存在'}")
    print(f"  {'✓' if env_file.exists() else '✗'} .env: {'存在' if env_file.exists() else '不存在（请从.env.example复制）'}")
    print(f"  ℹ .openai: {'存在（兼容）' if openai_file.exists() else '不存在'}")

    # 加载环境变量
    if env_file.exists():
        load_dotenv(env_file)
        print("\n✓ 已加载 .env 文件")
    elif openai_file.exists():
        load_dotenv(openai_file)
        print("\n✓ 已加载 .openai 文件（兼容模式）")
    else:
        print("\n✗ 未找到配置文件")
        return False

    # 检查环境变量
    print("\n环境变量检查:")

    # OpenAI配置
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_base = os.getenv("OPENAI_API_BASE")
    print(f"  {'✓' if openai_key else '✗'} OPENAI_API_KEY: {'已配置' if openai_key else '未配置'}")
    print(f"  {'✓' if openai_base else 'ℹ'} OPENAI_API_BASE: {openai_base if openai_base else '未配置（将使用默认值）'}")

    # Semantic Scholar配置
    semantic_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    print(f"  {'✓' if semantic_key and semantic_key != 'your_semantic_scholar_api_key_here' else '✗'} SEMANTIC_SCHOLAR_API_KEY: {'已配置' if semantic_key and semantic_key != 'your_semantic_scholar_api_key_here' else '未配置'}")

    # 测试工具导入
    print("\n工具导入测试:")
    try:
        from tools.semanticscholar import SemanticScholarSearchTool
        tool = SemanticScholarSearchTool()
        print(f"  ✓ SemanticScholar工具导入成功")
        print(f"    工具名称: {tool.name}")
        print(f"    API配置: {'已配置' if tool.api_key else '未配置'}")
    except Exception as e:
        print(f"  ✗ 工具导入失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("配置验证完成！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = verify_environment()
    exit(0 if success else 1)
