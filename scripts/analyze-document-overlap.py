#!/usr/bin/env python3
"""
Document Overlap Analysis Script

Analyzes B0.3-labeled documents to identify duplicate content, overlapping sections,
and contradictory information for consolidation planning.

Output: JSON mapping of duplicate sections across documents.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import difflib

# Configuration
REPO_ROOT = Path(__file__).parent.parent
B0_3_PATTERN = re.compile(r'B0\.3', re.IGNORECASE)
EXCLUDE_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', '.venv', 'docs/archive'}
MIN_SIMILARITY_THRESHOLD = 0.7  # 70% similarity considered duplicate
MIN_SECTION_LENGTH = 100  # Minimum characters for section comparison


def find_b0_3_documents(root: Path) -> List[Path]:
    """Find all files containing B0.3 labels."""
    documents = []
    
    for file_path in root.rglob('*.md'):
        # Skip excluded directories
        if any(excluded in str(file_path) for excluded in EXCLUDE_DIRS):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if B0_3_PATTERN.search(content):
                    documents.append(file_path)
        except (UnicodeDecodeError, PermissionError):
            continue
    
    return documents


def extract_sections(content: str, file_path: Path) -> List[Dict]:
    """Extract logical sections from markdown document."""
    sections = []
    lines = content.split('\n')
    current_section = {'title': 'Introduction', 'content': '', 'line_start': 1}
    
    for i, line in enumerate(lines, 1):
        # Detect section headers (markdown headers)
        if line.startswith('#'):
            # Save previous section
            if current_section['content'].strip():
                current_section['line_end'] = i - 1
                sections.append(current_section.copy())
            
            # Start new section
            level = len(line) - len(line.lstrip('#'))
            title = line.lstrip('#').strip()
            current_section = {
                'title': title,
                'content': '',
                'line_start': i,
                'level': level
            }
        else:
            current_section['content'] += line + '\n'
    
    # Save last section
    if current_section['content'].strip():
        current_section['line_end'] = len(lines)
        sections.append(current_section)
    
    return sections


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts."""
    return difflib.SequenceMatcher(None, text1, text2).ratio()


def find_duplicate_sections(documents: List[Path]) -> Dict:
    """Find duplicate and overlapping sections across documents."""
    document_sections = {}
    overlap_map = defaultdict(list)
    
    # Extract sections from all documents
    for doc_path in documents:
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
                sections = extract_sections(content, doc_path)
                document_sections[str(doc_path)] = sections
        except Exception as e:
            print(f"Warning: Could not process {doc_path}: {e}")
            continue
    
    # Compare sections across documents
    doc_paths = list(document_sections.keys())
    for i, doc1_path in enumerate(doc_paths):
        for doc2_path in doc_paths[i+1:]:
            sections1 = document_sections[doc1_path]
            sections2 = document_sections[doc2_path]
            
            for sec1 in sections1:
                if len(sec1['content']) < MIN_SECTION_LENGTH:
                    continue
                
                for sec2 in sections2:
                    if len(sec2['content']) < MIN_SECTION_LENGTH:
                        continue
                    
                    similarity = calculate_similarity(sec1['content'], sec2['content'])
                    
                    if similarity >= MIN_SIMILARITY_THRESHOLD:
                        overlap_key = (
                            doc1_path,
                            sec1['title'],
                            doc2_path,
                            sec2['title']
                        )
                        overlap_map[overlap_key].append({
                            'similarity': similarity,
                            'section1': {
                                'title': sec1['title'],
                                'lines': f"{sec1['line_start']}-{sec1.get('line_end', '?')}",
                                'content_hash': hashlib.md5(sec1['content'].encode()).hexdigest()[:8]
                            },
                            'section2': {
                                'title': sec2['title'],
                                'lines': f"{sec2['line_start']}-{sec2.get('line_end', '?')}",
                                'content_hash': hashlib.md5(sec2['content'].encode()).hexdigest()[:8]
                            }
                        })
    
    return {
        'documents_analyzed': len(documents),
        'total_documents': len(document_sections),
        'overlaps': dict(overlap_map),
        'document_sections': {
            path: [{'title': s['title'], 'lines': f"{s['line_start']}-{s.get('line_end', '?')}"} 
                   for s in sections]
            for path, sections in document_sections.items()
        }
    }


def categorize_documents(documents: List[Path]) -> Dict[str, List[str]]:
    """Categorize documents by type for consolidation planning."""
    categories = {
        'pii_implementation': [],
        'schema_governance': [],
        'exit_gates': [],
        'implementation_summaries': [],
        'forensic_analysis': [],
        'other': []
    }
    
    for doc_path in documents:
        doc_name = doc_path.name.lower()
        doc_str = str(doc_path)
        
        if 'pii' in doc_name or 'pii' in doc_str.lower():
            categories['pii_implementation'].append(str(doc_path))
        elif 'schema' in doc_name or 'governance' in doc_name:
            categories['schema_governance'].append(str(doc_path))
        elif 'exit_gate' in doc_name or 'phase_' in doc_name:
            categories['exit_gates'].append(str(doc_path))
        elif 'implementation_complete' in doc_name or 'implementation_summary' in doc_name:
            categories['implementation_summaries'].append(str(doc_path))
        elif 'forensic' in doc_name:
            categories['forensic_analysis'].append(str(doc_path))
        else:
            categories['other'].append(str(doc_path))
    
    return categories


def generate_consolidation_recommendations(overlap_analysis: Dict, categories: Dict) -> Dict:
    """Generate recommendations for document consolidation."""
    recommendations = {
        'pii_controls': {
            'target_file': 'docs/database/pii-controls.md',
            'source_files': categories['pii_implementation'],
            'rationale': 'All PII implementation details should be consolidated into single authoritative document'
        },
        'schema_governance': {
            'target_file': 'docs/database/schema-governance.md',
            'source_files': categories['schema_governance'],
            'rationale': 'Schema governance rules scattered across multiple files should be unified'
        },
        'migration_validation': {
            'target_file': 'docs/database/migration-validation.md',
            'source_files': categories['exit_gates'],
            'rationale': 'Exit gate verification procedures should be consolidated for operational clarity'
        },
        'implementation_history': {
            'target_file': 'docs/archive/implementation-phases/b0.3/',
            'source_files': categories['implementation_summaries'] + categories['forensic_analysis'],
            'rationale': 'Historical implementation documents should be archived with metadata'
        }
    }
    
    return recommendations


def main():
    """Main execution function."""
    print("Analyzing B0.3 document overlap...")
    
    # Find all B0.3 documents
    documents = find_b0_3_documents(REPO_ROOT)
    print(f"Found {len(documents)} documents with B0.3 labels")
    
    # Categorize documents
    categories = categorize_documents(documents)
    print(f"\nDocument categories:")
    for cat, files in categories.items():
        print(f"  {cat}: {len(files)} files")
    
    # Find duplicate sections
    print("\nAnalyzing section overlaps...")
    overlap_analysis = find_duplicate_sections(documents)
    
    # Generate recommendations
    recommendations = generate_consolidation_recommendations(overlap_analysis, categories)
    
    # Compile final report
    report = {
        'analysis_date': str(Path(__file__).stat().st_mtime),
        'documents_found': len(documents),
        'document_list': [str(d) for d in documents],
        'categories': categories,
        'overlap_analysis': overlap_analysis,
        'consolidation_recommendations': recommendations
    }
    
    # Output JSON report
    output_file = REPO_ROOT / 'docs' / 'archive' / 'implementation-phases' / 'b0.3' / 'overlap-analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nAnalysis complete. Report saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  - Documents analyzed: {overlap_analysis['documents_analyzed']}")
    print(f"  - Overlapping sections found: {len(overlap_analysis['overlaps'])}")
    print(f"  - Consolidation targets: {len(recommendations)}")
    
    return report


if __name__ == '__main__':
    main()

