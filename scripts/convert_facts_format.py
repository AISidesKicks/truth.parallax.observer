#!/usr/bin/env python3
"""
Convert /facts from old format to new format with centralized metadata.

Old:
  wisdom-name/
  ├── .abstract      (YAML frontmatter + content)
  ├── .overview      (YAML frontmatter + content)
  └── content.md     (YAML frontmatter + content)

New:
  wisdom-name/
  ├── .metadata.yaml (centralized metadata)
  ├── l0.abstract    (L0 Essence - pure content)
  ├── l1.overview    (L1 Insight - pure content)
  └── l2.content.md  (L2 Depth - pure content)

Wisdom Terminology:
- L0 Essence: Core claim (~100 tokens)
- L1 Insight: Context, hooks, counter-arguments (~500 tokens)
- L2 Depth: Full explanation (max 2K tokens)

Usage:
    python scripts/convert_facts_format.py --dry-run    # Preview changes
    python scripts/convert_facts_format.py             # Convert all
    python scripts/convert_facts_format.py --validate  # Validate new format
"""

import argparse
import logging
import re
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

FACTS_DIR = Path("facts")


def extract_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (metadata, pure_content)."""
    if not content.startswith("---"):
        return {}, content
    
    match = re.match(r'^---\n(.*?)\n---\n?(.*)$', content, re.DOTALL)
    if not match:
        return {}, content
    
    yaml_text = match.group(1)
    pure_content = match.group(2)
    
    metadata = {}
    for line in yaml_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if key == 'tokens':
                metadata[key] = int(value)
            else:
                metadata[key] = value
    
    return metadata, pure_content


def convert_chunk(chunk_dir: Path, dry_run: bool = False) -> dict:
    """Convert a single chunk directory to new format."""
    
    old_files = {
        'l0': chunk_dir / '.abstract',
        'l1': chunk_dir / '.overview',
        'l2': chunk_dir / 'content.md',
    }
    
    # Check if old format exists
    if not all(f.exists() for f in old_files.values()):
        # Check if already converted
        if (chunk_dir / '.metadata.yaml').exists():
            return {'status': 'already_converted', 'dir': str(chunk_dir)}
        return {'status': 'missing_files', 'dir': str(chunk_dir)}
    
    # Read old files
    tier_metadata = {}
    tier_content = {}
    
    for tier, old_path in old_files.items():
        content = old_path.read_text()
        metadata, pure_content = extract_frontmatter(content)
        tier_metadata[tier] = metadata
        tier_content[tier] = pure_content
    
    # Build unified metadata
    base_metadata = tier_metadata.get('l2', tier_metadata.get('l1', tier_metadata.get('l0', {})))
    
    metadata = {
        'uri': base_metadata.get('uri', ''),
        'source': base_metadata.get('source', ''),
        'target': base_metadata.get('target', ''),
        'category': base_metadata.get('category', ''),
        'chunk_name': chunk_dir.name,
        'generated': base_metadata.get('generated', datetime.now().strftime('%Y-%m-%d')),
        'tiers': {}
    }
    
    for tier in ['l0', 'l1', 'l2']:
        metadata['tiers'][tier] = {
            'file': f'{tier}.abstract' if tier == 'l0' else f'{tier}.overview' if tier == 'l1' else f'{tier}.content.md',
            'tokens': tier_metadata.get(tier, {}).get('tokens', 0),
        }
    
    # New file paths
    new_files = {
        'metadata': chunk_dir / '.metadata.yaml',
        'l0': chunk_dir / 'l0.abstract',
        'l1': chunk_dir / 'l1.overview',
        'l2': chunk_dir / 'l2.content.md',
    }
    
    if dry_run:
        logger.info(f"Would convert: {chunk_dir}")
        return {'status': 'dry_run', 'dir': str(chunk_dir)}
    
    # Write .metadata.yaml
    yaml_content = format_yaml(metadata)
    new_files['metadata'].write_text(yaml_content)
    
    # Write tier content files (pure content, no frontmatter)
    new_files['l0'].write_text(tier_content['l0'])
    new_files['l1'].write_text(tier_content['l1'])
    new_files['l2'].write_text(tier_content['l2'])
    
    # Remove old files
    for old_path in old_files.values():
        old_path.unlink()
    
    return {
        'status': 'converted',
        'dir': str(chunk_dir),
        'metadata': metadata,
    }


def format_yaml(metadata: dict) -> str:
    """Format metadata dict as YAML string."""
    lines = [f"{k}: {v}" for k, v in metadata.items() if k != 'tiers']
    lines.append("tiers:")
    
    for tier, info in metadata.get('tiers', {}).items():
        lines.append(f"  {tier}:")
        lines.append(f"    file: {info['file']}")
        lines.append(f"    tokens: {info['tokens']}")
    
    return '\n'.join(lines) + '\n'


def find_chunk_directories() -> list[Path]:
    """Find all chunk directories in facts/."""
    chunks = []
    
    for tier_file in FACTS_DIR.rglob('.abstract'):
        chunk_dir = tier_file.parent
        chunks.append(chunk_dir)
    
    # Also find already-converted chunks
    for metadata_file in FACTS_DIR.rglob('.metadata.yaml'):
        chunk_dir = metadata_file.parent
        if chunk_dir not in chunks:
            chunks.append(chunk_dir)
    
    return sorted(set(chunks))


def convert_all(dry_run: bool = False) -> dict:
    """Convert all chunk directories."""
    chunks = find_chunk_directories()
    
    results = {
        'converted': 0,
        'already_converted': 0,
        'errors': 0,
        'details': [],
    }
    
    for chunk_dir in chunks:
        result = convert_chunk(chunk_dir, dry_run)
        results['details'].append(result)
        
        if result['status'] == 'converted':
            results['converted'] += 1
            logger.info(f"Converted: {chunk_dir.name}")
        elif result['status'] == 'already_converted':
            results['already_converted'] += 1
        else:
            results['errors'] += 1
            logger.warning(f"Error: {chunk_dir.name} - {result['status']}")
    
    return results


def validate_format() -> dict:
    """Validate all chunks are in new format."""
    chunks = find_chunk_directories()
    
    results = {
        'valid': 0,
        'invalid': 0,
        'errors': [],
    }
    
    for chunk_dir in chunks:
        errors = []
        
        # Check .metadata.yaml exists
        metadata_path = chunk_dir / '.metadata.yaml'
        if not metadata_path.exists():
            errors.append('Missing .metadata.yaml')
        else:
            content = metadata_path.read_text()
            required = ['uri:', 'source:', 'target:', 'tiers:']
            for field in required:
                if field not in content:
                    errors.append(f'Metadata missing {field.rstrip(":")}')
        
        # Check tier files exist
        tier_files = {
            'l0': chunk_dir / 'l0.abstract',
            'l1': chunk_dir / 'l1.overview',
            'l2': chunk_dir / 'l2.content.md',
        }
        
        for tier, path in tier_files.items():
            if not path.exists():
                errors.append(f'Missing {tier} file')
            else:
                content = path.read_text()
                if content.startswith('---'):
                    errors.append(f'{tier} file has frontmatter (should be pure content)')
        
        # Check old files removed
        old_files = ['.abstract', '.overview', 'content.md']
        for old in old_files:
            if (chunk_dir / old).exists():
                errors.append(f'Old file still exists: {old}')
        
        if errors:
            results['invalid'] += 1
            results['errors'].append({
                'dir': str(chunk_dir),
                'errors': errors
            })
        else:
            results['valid'] += 1
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Convert facts to new format")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying')
    parser.add_argument('--validate', action='store_true', help='Validate new format')
    
    args = parser.parse_args()
    
    if args.validate:
        logger.info("Validating facts format...")
        results = validate_format()
        logger.info(f"Valid: {results['valid']}, Invalid: {results['invalid']}")
        
        if results['errors']:
            for err in results['errors'][:10]:
                logger.warning(f"  {err['dir']}: {err['errors']}")
    else:
        if args.dry_run:
            logger.info("Dry run - no changes will be made")
        
        results = convert_all(args.dry_run)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Converted: {results['converted']}")
        logger.info(f"Already converted: {results['already_converted']}")
        logger.info(f"Errors: {results['errors']}")


if __name__ == "__main__":
    main()
