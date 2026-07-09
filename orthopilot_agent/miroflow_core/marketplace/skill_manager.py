"""
Skill 管理器 - 遵循 Agent Skills Marketplace 标准
支持 Progressive Disclosure（渐进式加载）和热重载
"""

from pathlib import Path
from typing import Dict, List, Optional
import re
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class SkillMetadata:
    """Skill 元信息（用于 progressive disclosure 的第一阶段）"""

    def __init__(self, name: str, description: str, path: Path, version: str = "1.0.0", category: str = "", icon: str = "⚡"):
        self.name = name
        self.description = description
        self.path = path
        self.version = version
        self.category = category
        self.icon = icon

    def to_prompt_summary(self) -> str:
        """生成用于 prompt 的简短摘要"""
        return f"- {self.name} (v{self.version})\n  {self.description}\n  Path: {self.path}"

    def dict(self):
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "path": str(self.path),
            "version": self.version,
            "category": self.category,
            "icon": self.icon,
        }


class SkillDefinition:
    """Skill 完整定义（按需加载）"""

    def __init__(self, skill_dir: Path, lang: str = "en"):
        self.skill_dir = skill_dir
        self.skill_md_path = self._resolve_skill_md_path(skill_dir, lang)

        # 解析 SKILL.md 文件
        self.metadata, self.content = self._parse_skill_md()

    def _resolve_skill_md_path(self, skill_dir: Path, lang: str) -> Path:
        normalized = (lang or "en").lower()
        localized_path = skill_dir / "SKILL.md"
        english_path = skill_dir / "SKILL.en.md"

        if normalized == "en":
            if english_path.exists():
                return english_path
            if localized_path.exists():
                return localized_path
        else:
            if localized_path.exists():
                return localized_path
            if english_path.exists():
                return english_path

        return english_path if normalized == "en" else localized_path

    def _parse_skill_md(self) -> tuple:
        """解析 SKILL.md 文件，提取 metadata 和各层内容"""
        if not self.skill_md_path.exists():
            return {}, {}

        content = self.skill_md_path.read_text(encoding='utf-8')

        # 提取 YAML frontmatter (metadata)
        metadata_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if metadata_match:
            metadata_yaml = metadata_match.group(1)
            body = metadata_match.group(2)
            metadata = yaml.safe_load(metadata_yaml)
        else:
            metadata = {}
            body = content

        # 解析 Markdown 内容的各个层次
        parsed_content = {
            'description': self._extract_section(body, 'Description'),
            'system_prompt': self._extract_section(body, 'System Prompt'),
            'required_tools': self._extract_section(body, 'Required Tools'),
            'examples': self._extract_section(body, 'Examples'),
            'reference': self._extract_section(body, 'Reference'),
            'assets': self._extract_section(body, 'Assets'),
            'full_content': body  # 保存完整内容用于注入
        }

        return metadata, parsed_content

    def _extract_section(self, content: str, section_name: str) -> str:
        """从 Markdown 中提取指定章节的内容"""
        pattern = rf'## {section_name}\n(.*?)(?=\n## |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    @property
    def name(self) -> str:
        return self.metadata.get('name', '')

    @property
    def version(self) -> str:
        return self.metadata.get('version', '1.0.0')

    @property
    def dependencies(self) -> Dict[str, List[str]]:
        return self.metadata.get('dependencies', {})

    @property
    def system_prompt(self) -> str:
        return self.content.get('system_prompt', '')

    @property
    def full_content(self) -> str:
        """返回完整的 SKILL.md 内容（用于按需加载）"""
        return self.content.get('full_content', '')


class SkillManager:
    """Skill 管理器 - 支持 Progressive Disclosure 和热重载"""

    def __init__(self, skills_dir: Path = None):
        # Skills 目录
        self.skills_dir = skills_dir or Path("skills")

        # Skill 元信息注册表 (name -> SkillMetadata) - 始终加载
        self.skill_metadata: Dict[str, SkillMetadata] = {}
        self.skill_dirs: Dict[str, Path] = {}

        # Skill 完整定义缓存 ((name, lang) -> SkillDefinition) - 按需加载
        self.skill_definitions: Dict[tuple[str, str], SkillDefinition] = {}

        # 文件监控器（用于热重载）
        self.observer = None

        # 加载所有 Skills 的元信息
        self._load_all_metadata()

        # 启动热重载监控
        self._start_hot_reload()

    def _load_all_metadata(self):
        """加载所有 Skills 的元信息（只读取 YAML frontmatter）"""
        if not self.skills_dir.exists():
            print(f"Skills directory {self.skills_dir} does not exist, creating it...")
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return

        self.skill_metadata.clear()
        self.skill_dirs.clear()

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            skill_md_en = skill_dir / "SKILL.en.md"
            if not skill_md.exists() and not skill_md_en.exists():
                continue

            try:
                skill_md_path = SkillDefinition(skill_dir, 'en').skill_md_path
                content = skill_md_path.read_text(encoding='utf-8')
                metadata_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
                if metadata_match:
                    metadata = yaml.safe_load(metadata_match.group(1))
                    skill_name = metadata.get('name', skill_dir.name)
                    self.skill_dirs[skill_name] = skill_dir
                    skill_meta = self._load_skill_metadata(skill_dir, lang='en')
                    self.skill_metadata[skill_name] = skill_meta
                    print(f"Loaded skill metadata: {skill_meta.name} v{skill_meta.version}")
            except Exception as e:
                print(f"Failed to load skill metadata from {skill_dir}: {e}")

    def _load_skill_metadata(self, skill_dir: Path, lang: str = 'en') -> SkillMetadata:
        skill_md_path = SkillDefinition(skill_dir, lang).skill_md_path
        content = skill_md_path.read_text(encoding='utf-8')
        metadata_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        metadata = yaml.safe_load(metadata_match.group(1)) if metadata_match else {}
        return SkillMetadata(
            name=metadata.get('name', skill_dir.name),
            description=metadata.get('description', ''),
            path=skill_dir,
            version=metadata.get('version', '1.0.0'),
            category=metadata.get('category', ''),
            icon=metadata.get('icon', '⚡'),
        )

    def get_skill_metadata(self, skill_name: str, lang: str = 'en') -> Optional[SkillMetadata]:
        """获取 Skill 元信息（不触发完整加载）"""
        skill_dir = self.skill_dirs.get(skill_name)
        if not skill_dir:
            return None
        return self._load_skill_metadata(skill_dir, lang=lang)

    def load_skill_full(self, skill_name: str, lang: str = 'en') -> Optional[SkillDefinition]:
        """按需加载 Skill 的完整定义"""
        cache_key = (skill_name, (lang or 'en').lower())
        if cache_key in self.skill_definitions:
            return self.skill_definitions[cache_key]

        skill_dir = self.skill_dirs.get(skill_name)
        if not skill_dir:
            return None

        try:
            skill_def = SkillDefinition(skill_dir, lang=lang)
            self.skill_definitions[cache_key] = skill_def
            print(f"Loaded full skill definition: {skill_name} [{cache_key[1]}]")
            return skill_def
        except Exception as e:
            print(f"Failed to load full skill definition for {skill_name}: {e}")
            return None

    def list_skills(self, category: Optional[str] = None, lang: str = 'en') -> List[SkillMetadata]:
        """列出所有 Skills 的元信息"""
        skills = [self._load_skill_metadata(skill_dir, lang=lang) for skill_dir in self.skill_dirs.values()]
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    def list_skills_summary(self, category: Optional[str] = None, lang: str = 'en') -> str:
        """生成所有 Skills 的摘要（用于注入到 system prompt）"""
        skills = self.list_skills(category, lang=lang)

        if not skills:
            return ""

        summary = "# Available Skills\n\n"
        for skill_meta in skills:
            summary += skill_meta.to_prompt_summary() + "\n\n"

        return summary

    def resolve_dependencies(self, skill_name: str) -> List[str]:
        """解析 Skill 的工具依赖（支持 semver）"""
        skill = self.load_skill_full(skill_name, lang='en')
        if not skill:
            return []

        tool_deps = skill.dependencies.get('tools', [])
        resolved_tools = []

        for dep in tool_deps:
            # 解析 "tool-name@^1.0.0" 格式
            if "@" in dep:
                tool_name, version_spec = dep.split("@", 1)
            else:
                tool_name = dep
                version_spec = "*"

            # TODO: 实现版本匹配逻辑
            resolved_tools.append(tool_name)

        return resolved_tools

    def _start_hot_reload(self):
        """启动热重载监控"""
        class SkillReloadHandler(FileSystemEventHandler):
            def __init__(self, skill_manager):
                self.skill_manager = skill_manager

            def on_modified(self, event):
                if event.src_path.endswith("SKILL.md") or event.src_path.endswith("SKILL.en.md"):
                    print(f"Detected skill change: {event.src_path}")
                    # 清除缓存，重新加载元信息
                    self.skill_manager.skill_definitions.clear()
                    self.skill_manager._load_all_metadata()

        handler = SkillReloadHandler(self)

        if self.skills_dir.exists():
            self.observer = Observer()
            self.observer.schedule(handler, str(self.skills_dir), recursive=True)
            self.observer.start()
            print(f"Started hot reload monitoring for {self.skills_dir}")

    def inject_skill_to_context(self, base_prompt: str, skill_name: str) -> str:
        """将指定 Skill 的完整内容注入到上下文（按需加载）"""
        skill = self.load_skill_full(skill_name, lang='en')
        if not skill:
            return base_prompt

        # 注入完整的 SKILL.md 内容
        skill_content = f"\n\n# Active Skill: {skill.name}\n\n{skill.full_content}"
        return base_prompt + skill_content

    def stop(self):
        """停止热重载监控"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
