import asyncio
from playwright.async_api import async_playwright
import json
from typing import Dict, List, Any
from dataclasses import dataclass
import boto3
import json
import requests
from bs4 import BeautifulSoup
import sys
from urllib.parse import urljoin, urlparse, unquote
import re
import os
import argparse

from botocore.exceptions import ClientError
from pathlib import Path
import shutil
from datetime import datetime
import logging
from tqdm import tqdm


@dataclass
class LayoutIssue:
    element_selector: str
    issue_type: str
    description: str
    computed_styles: Dict
    bounding_box: Dict
    severity: str
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class RealTimeCSSAnalyzer:
    
    """
    Real-time CSS analysis using browser automation to detect actual layout issues
    as they appear in the rendered page, not just in the source code.
    """
    
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        profile_name: str = None,
        cache_dir: str = ".cache",
    ):
        """Initialize browser viewport sizes and AWS Bedrock client"""
        # Viewport settings
        self.browser = None
        self.page = None
        self.viewport_sizes = [
            {"width": 1920, "height": 1080, "name": "desktop"},
            {"width": 768, "height": 1024, "name": "tablet"},
            {"width": 375, "height": 667, "name": "mobile"}
        ]

        # AWS Bedrock client setup
        try:
            if profile_name:
                session = boto3.Session(profile_name=profile_name)
                self.bedrock_client = session.client(
                    "bedrock-runtime", region_name=region_name
                )
            else:
                self.bedrock_client = boto3.client(
                    "bedrock-runtime", region_name=region_name
                )

            self.model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
            self.cache_dir = cache_dir
            os.makedirs(self.cache_dir, exist_ok=True)

            logger.info(f"AWS Bedrock client initialized for region: {region_name}")
            logger.info(f"Cache directory set to: {self.cache_dir}")

        except Exception as e:
            logger.error(f"Failed to initialize AWS Bedrock client: {str(e)}")
            raise

    def normalize_to_url(self, path_or_url: str) -> str:
        """Convert local file paths to proper file:// URLs for browser navigation"""
        if path_or_url.startswith(('http://', 'https://', 'file://')):
            return path_or_url
        # Convert local path to absolute path and then to file:// URL
        import os
        abs_path = os.path.abspath(path_or_url)
        return f"file://{abs_path}"

    async def analyze_page_realtime(self, url: str) -> Dict[str, Any]:
        """Main method to perform real-time CSS analysis"""
        
        async with async_playwright() as p:
            # Normalize the URL for browser navigation
            normalized_url = self.normalize_to_url(url)
            self.browser = await p.chromium.launch(headless=False)  # Non-headless for debugging
            self.page = await self.browser.new_page()
            
            try:
                await self.page.goto(normalized_url, wait_until='networkidle')
                
                # Comprehensive real-time analysis
                analysis_results = {
                    "computed_style_issues": await self._analyze_computed_styles(),
                    "layout_geometry_issues": await self._analyze_layout_geometry(),
                    "responsive_issues": await self._analyze_responsive_behavior(),
                    "performance_issues": await self._analyze_layout_performance(),
                    "visual_issues": await self._analyze_visual_problems(),
                    "accessibility_layout": await self._analyze_accessibility_layout(),
                    "dynamic_behavior": await self._analyze_dynamic_behavior(),
                    "cross_browser_issues": await self._simulate_browser_differences()
                }
                
                return analysis_results
                
            finally:
                await self.browser.close()
    
    async def _analyze_computed_styles(self) -> List[LayoutIssue]:
        """Analyze actual computed styles vs intended styles"""
        
        # JavaScript to run in browser - gets computed styles for all elements
        js_computed_analysis = """
        () => {
            const issues = [];
            const elements = document.querySelectorAll('*');
            
            elements.forEach((el, index) => {
                const computed = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                
                // Issue 1: Elements with zero dimensions but content
                if ((rect.width === 0 || rect.height === 0) && el.textContent.trim()) {
                    issues.push({
                        selector: `element-${index}`,
                        tagName: el.tagName,
                        issue: 'zero-dimension-with-content',
                        description: 'Element has content but zero width/height',
                        computed: {
                            width: computed.width,
                            height: computed.height,
                            display: computed.display,
                            visibility: computed.visibility
                        },
                        boundingBox: rect,
                        textContent: el.textContent.trim().substring(0, 50)
                    });
                }
                
                // Issue 2: Conflicting positioning
                if (computed.position === 'absolute' && computed.position === 'relative') {
                    issues.push({
                        selector: `element-${index}`,
                        issue: 'conflicting-position',
                        description: 'Element has conflicting position values',
                        computed: {
                            position: computed.position,
                            top: computed.top,
                            left: computed.left,
                            zIndex: computed.zIndex
                        }
                    });
                }
                
                // Issue 3: Overflow issues
                if (computed.overflow === 'visible' && 
                    (rect.width > el.parentElement?.getBoundingClientRect().width ||
                     rect.height > el.parentElement?.getBoundingClientRect().height)) {
                    issues.push({
                        selector: `element-${index}`,
                        issue: 'overflow-visible-spillage',
                        description: 'Element overflows parent with overflow:visible',
                        computed: {
                            overflow: computed.overflow,
                            overflowX: computed.overflowX,
                            overflowY: computed.overflowY
                        },
                        boundingBox: rect
                    });
                }
                
                // Issue 4: Invisible text due to color contrast
                const bgColor = computed.backgroundColor;
                const textColor = computed.color;
                if (bgColor === textColor && textColor !== 'rgba(0, 0, 0, 0)') {
                    issues.push({
                        selector: `element-${index}`,
                        issue: 'invisible-text',
                        description: 'Text color matches background color',
                        computed: {
                            color: textColor,
                            backgroundColor: bgColor
                        }
                    });
                }
                
                // Issue 5: Elements outside viewport
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                
                if (rect.left >= viewportWidth || rect.top >= viewportHeight || 
                    rect.right <= 0 || rect.bottom <= 0) {
                    issues.push({
                        selector: `element-${index}`,
                        issue: 'outside-viewport',
                        description: 'Element is completely outside viewport',
                        boundingBox: rect,
                        viewport: { width: viewportWidth, height: viewportHeight }
                    });
                }
            });
            
            return issues;
        }
        """
        
        computed_issues = await self.page.evaluate(js_computed_analysis)
        
        # Convert to LayoutIssue objects
        layout_issues = []
        for issue in computed_issues:
            layout_issues.append(LayoutIssue(
                element_selector=issue.get('selector', ''),
                issue_type=issue.get('issue', ''),
                description=issue.get('description', ''),
                computed_styles=issue.get('computed', {}),
                bounding_box=issue.get('boundingBox', {}),
                severity=self._calculate_severity(issue.get('issue', '')),
        
            ))
        
        return layout_issues
    
    async def _analyze_layout_geometry(self) -> List[Dict]:
        """Analyze actual element positioning and spacing"""
        
        js_geometry_analysis = """
        () => {
            const issues = [];
            const elements = Array.from(document.querySelectorAll('*'));
            
            // Check for overlapping elements
            for (let i = 0; i < elements.length; i++) {
                const el1 = elements[i];
                const rect1 = el1.getBoundingClientRect();
                
                // Skip if element is not visible
                if (rect1.width === 0 || rect1.height === 0) continue;
                
                for (let j = i + 1; j < elements.length; j++) {
                    const el2 = elements[j];
                    const rect2 = el2.getBoundingClientRect();
                    
                    // Skip if element is not visible or is child of el1
                    if (rect2.width === 0 || rect2.height === 0 || el1.contains(el2) || el2.contains(el1)) continue;
                    
                    // Check for overlap
                    const overlap = !(rect1.right <= rect2.left || 
                                    rect2.right <= rect1.left || 
                                    rect1.bottom <= rect2.top || 
                                    rect2.bottom <= rect1.top);
                    
                    if (overlap) {
                        const overlapArea = Math.max(0, Math.min(rect1.right, rect2.right) - Math.max(rect1.left, rect2.left)) *
                                          Math.max(0, Math.min(rect1.bottom, rect2.bottom) - Math.max(rect1.top, rect2.top));
                        
                        if (overlapArea > 100) { // Only report significant overlaps
                            issues.push({
                                issue: 'element-overlap',
                                description: `Elements overlap by ${overlapArea}px²`,
                                element1: {
                                    tagName: el1.tagName,
                                    className: el1.className,
                                    boundingBox: rect1
                                },
                                element2: {
                                    tagName: el2.tagName,
                                    className: el2.className,
                                    boundingBox: rect2
                                },
                                overlapArea: overlapArea
                            });
                        }
                    }
                }
            }
            
            // Check for elements with negative margins causing layout issues
            elements.forEach((el, index) => {
                const computed = window.getComputedStyle(el);
                const marginTop = parseInt(computed.marginTop);
                const marginLeft = parseInt(computed.marginLeft);
                
                if (marginTop < -50 || marginLeft < -50) {
                    const rect = el.getBoundingClientRect();
                    issues.push({
                        issue: 'extreme-negative-margin',
                        description: `Element has extreme negative margin (top: ${marginTop}px, left: ${marginLeft}px)`,
                        element: {
                            tagName: el.tagName,
                            className: el.className,
                            boundingBox: rect
                        },
                        margins: {
                            top: marginTop,
                            left: marginLeft
                        }
                    });
                }
            });
            
            return issues;
        }
        """
        
        return await self.page.evaluate(js_geometry_analysis)
    
    async def _analyze_responsive_behavior(self) -> List[Dict]:
        """Test responsive behavior across different viewport sizes"""
        
        responsive_issues = []
        
        for viewport in self.viewport_sizes:
            await self.page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
            await self.page.wait_for_timeout(500)  # Wait for layout to settle
            
            # Analyze layout at this viewport size
            js_responsive_check = f"""
            () => {{
                const issues = [];
                const viewportName = '{viewport["name"]}';
                const elements = document.querySelectorAll('*');
                
                elements.forEach((el, index) => {{
                    const rect = el.getBoundingClientRect();
                    const computed = window.getComputedStyle(el);
                    
                    // Check for horizontal scrolling issues
                    if (rect.right > window.innerWidth) {{
                        issues.push({{
                            viewport: viewportName,
                            issue: 'horizontal-overflow',
                            description: `Element extends beyond viewport width at ${{viewportName}}`,
                            element: {{
                                tagName: el.tagName,
                                className: el.className,
                                boundingBox: rect
                            }},
                            overflow: rect.right - window.innerWidth
                        }});
                    }}
                    
                    // Check for text that becomes unreadable
                    if (computed.fontSize && parseInt(computed.fontSize) < 12 && viewportName === 'mobile') {{
                        issues.push({{
                            viewport: viewportName,
                            issue: 'text-too-small',
                            description: `Text too small on mobile (${{computed.fontSize}})`,
                            element: {{
                                tagName: el.tagName,
                                className: el.className
                            }},
                            fontSize: computed.fontSize
                        }});
                    }}
                    
                    // Check for touch targets too small on mobile
                    if (viewportName === 'mobile' && 
                        (el.tagName === 'BUTTON' || el.tagName === 'A') &&
                        (rect.width < 44 || rect.height < 44)) {{
                        issues.push({{
                            viewport: viewportName,
                            issue: 'touch-target-too-small',
                            description: `Interactive element too small for touch (${{rect.width}}x${{rect.height}})`,
                            element: {{
                                tagName: el.tagName,
                                className: el.className,
                                boundingBox: rect
                            }}
                        }});
                    }}
                }});
                
                return issues;
            }}
            """
            
            viewport_issues = await self.page.evaluate(js_responsive_check)
            responsive_issues.extend(viewport_issues)
        
        return responsive_issues
    
    async def _analyze_layout_performance(self) -> List[Dict]:
        """Analyze layout performance issues that cause reflows/repaints"""
        
        # Start performance monitoring
        await self.page.evaluate("""
        () => {
            window.layoutMetrics = {
                reflows: 0,
                repaints: 0,
                startTime: performance.now()
            };
            
            // Monitor for layout thrashing
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (entry.entryType === 'measure' && entry.name.includes('layout')) {
                        window.layoutMetrics.reflows++;
                    }
                }
            });
            observer.observe({entryTypes: ['measure']});
        }
        """)
        
        # Simulate user interactions that might cause layout issues
        interactions = [
            lambda: self.page.mouse.move(100, 100),
            lambda: self.page.mouse.move(200, 200),
            lambda: self.page.keyboard.press('Tab'),
            lambda: self.page.keyboard.press('Tab'),
        ]
        
        for interaction in interactions:
            await interaction()
            await self.page.wait_for_timeout(100)
        
        # Analyze performance metrics
        performance_data = await self.page.evaluate("""
        () => {
            const issues = [];
            
            // Check for elements that cause layout thrashing
            const expensiveElements = document.querySelectorAll('*');
            expensiveElements.forEach((el, index) => {
                const computed = window.getComputedStyle(el);
                
                // Elements with transforms that might cause reflows
                if (computed.transform !== 'none' && computed.position !== 'fixed') {
                    issues.push({
                        issue: 'transform-reflow-risk',
                        description: 'Transform on non-fixed element may cause reflows',
                        element: {
                            tagName: el.tagName,
                            className: el.className
                        }
                    });
                }
                
                // Elements with percentage-based positioning
                if (computed.width.includes('%') && computed.position === 'absolute') {
                    issues.push({
                        issue: 'percentage-positioning',
                        description: 'Percentage-based absolute positioning can cause reflows',
                        element: {
                            tagName: el.tagName,
                            className: el.className
                        }
                    });
                }
            });
            
            return {
                issues: issues,
                metrics: window.layoutMetrics
            };
        }
        """)
        
        return performance_data.get('issues', [])
    
    async def _analyze_visual_problems(self) -> List[Dict]:
        """Analyze visual layout problems using screenshot comparison"""
        
        # Take screenshot for visual analysis
        screenshot = await self.page.screenshot(full_page=True)
        
        # Analyze for visual issues using JavaScript
        visual_issues = await self.page.evaluate("""
        () => {
            const issues = [];
            const elements = document.querySelectorAll('*');
            
            elements.forEach((el, index) => {
                const computed = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                
                // Check for elements that are visually hidden but not properly hidden
                if ((computed.opacity === '0' || computed.visibility === 'hidden') &&
                    rect.width > 0 && rect.height > 0) {
                    issues.push({
                        issue: 'visually-hidden-taking-space',
                        description: 'Element is visually hidden but still takes up space',
                        element: {
                            tagName: el.tagName,
                            className: el.className,
                            boundingBox: rect
                        }
                    });
                }
                
                // Check for broken aspect ratios on images
                if (el.tagName === 'IMG' && el.complete) {
                    const naturalRatio = el.naturalWidth / el.naturalHeight;
                    const displayRatio = rect.width / rect.height;
                    
                    if (Math.abs(naturalRatio - displayRatio) > 0.1) {
                        issues.push({
                            issue: 'image-aspect-ratio-distorted',
                            description: 'Image aspect ratio is distorted',
                            element: {
                                tagName: el.tagName,
                                src: el.src,
                                boundingBox: rect
                            },
                            ratios: {
                                natural: naturalRatio,
                                display: displayRatio
                            }
                        });
                    }
                }
            });
            
            return issues;
        }
        """)
        
        return visual_issues
    
    async def _analyze_accessibility_layout(self) -> List[Dict]:
        """Analyze layout issues that affect accessibility"""
        
        return await self.page.evaluate("""
        () => {
            const issues = [];
            const elements = document.querySelectorAll('*');
            
            elements.forEach((el, index) => {
                const computed = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                
                // Check for focus indicators that might be hidden
                // Check if element is focusable using proper criteria
                const isFocusable = (
                    el.tabIndex >= 0 || 
                    ['INPUT', 'BUTTON', 'SELECT', 'TEXTAREA', 'A'].includes(el.tagName) ||
                    el.contentEditable === 'true'
                ) && !el.disabled && el.style.display !== 'none' && el.style.visibility !== 'hidden';

                if (isFocusable) {
                    // Simulate focus to check if focus indicator is visible
                    const focusStyles = {
                        outline: computed.outline,
                        outlineOffset: computed.outlineOffset,
                        border: computed.border,
                        boxShadow: computed.boxShadow
                    };
                    
                    const hasFocusIndicator = focusStyles.outline !== 'none' ||
                                           focusStyles.border !== 'none' ||
                                           focusStyles.boxShadow !== 'none';
                    
                    if (!hasFocusIndicator) {
                        issues.push({
                            issue: 'missing-focus-indicator',
                            description: 'Focusable element lacks visible focus indicator',
                            element: {
                                tagName: el.tagName,
                                className: el.className
                            }
                        });
                    }
                }
                
                // Check for insufficient color contrast
                if (el.textContent && el.textContent.trim()) {
                    const textColor = computed.color;
                    const bgColor = computed.backgroundColor;
                    
                    // This is a simplified check - real contrast calculation is more complex
                    if (textColor && bgColor && textColor !== 'rgb(0, 0, 0)' && bgColor !== 'rgba(0, 0, 0, 0)') {
                        issues.push({
                            issue: 'potential-contrast-issue',
                            description: 'Potential color contrast issue detected',
                            element: {
                                tagName: el.tagName,
                                className: el.className
                            },
                            colors: {
                                text: textColor,
                                background: bgColor
                            }
                        });
                    }
                }
            });
            
            return issues;
        }
        """)
    
    async def _analyze_dynamic_behavior(self) -> List[Dict]:
        """Analyze how layout behaves with dynamic content changes"""
        
        # Test dynamic content insertion
        await self.page.evaluate("""
        () => {
            // Add some dynamic content to test layout stability
            const testDiv = document.createElement('div');
            testDiv.innerHTML = 'Dynamic content added for testing';
            testDiv.style.cssText = 'position: absolute; top: 0; left: 0; background: red; padding: 10px;';
            document.body.appendChild(testDiv);
            
            // Remove it after a moment
            setTimeout(() => {
                testDiv.remove();
            }, 100);
        }
        """)
        
        await self.page.wait_for_timeout(200)
        
        # Check for layout shift
        layout_shift_data = await self.page.evaluate("""
        () => {
            // This would normally use the Layout Instability API
            return {
                layoutShifts: [], // Placeholder for actual layout shift detection
                cumulativeLayoutShift: 0
            };
        }
        """)
        
        return []  # Placeholder for actual dynamic analysis
    
    async def _simulate_browser_differences(self) -> List[Dict]:
        """Simulate different browser rendering behaviors"""
        
        # This would involve testing with different user agents
        # For now, we'll check for browser-specific CSS that might cause issues
        
        return await self.page.evaluate("""
        () => {
            const issues = [];
            const styleSheets = Array.from(document.styleSheets);
            
            // Check for browser-specific prefixes
            styleSheets.forEach(sheet => {
                try {
                    const rules = Array.from(sheet.cssRules || []);
                    rules.forEach(rule => {
                        if (rule.cssText) {
                            const hasWebkit = rule.cssText.includes('-webkit-');
                            const hasMoz = rule.cssText.includes('-moz-');
                            const hasMs = rule.cssText.includes('-ms-');
                            
                            if (hasWebkit && !hasMoz && !hasMs) {
                                issues.push({
                                    issue: 'webkit-only-prefix',
                                    description: 'CSS rule only has webkit prefix, may not work in other browsers',
                                    rule: rule.cssText.substring(0, 100)
                                });
                            }
                        }
                    });
                } catch (e) {
                    // Cross-origin stylesheets might not be accessible
                }
            });
            
            return issues;
        }
        """)
    
    def _calculate_severity(self, issue_type: str) -> str:
        """Calculate severity based on issue type"""
        high_severity = ['outside-viewport', 'element-overlap', 'invisible-text']
        medium_severity = ['overflow-visible-spillage', 'zero-dimension-with-content']
        
        if issue_type in high_severity:
            return 'high'
        elif issue_type in medium_severity:
            return 'medium'
        else:
            return 'low'
    
    def create_bedrock_analysis_prompt(
        self,
        source: str,
        html_content: str,
        css_content: str,
        alignment_issues: Dict,
        content_type: str,
    ) -> str:
        """Create comprehensive prompt for Bedrock analysis"""

        issues_summary = ""
        for category, issue_list in alignment_issues.items():
            if issue_list:
                category_name = category.replace("_", " ").title()
                issues_summary += f"\n{category_name}:\n"
                for issue in issue_list:
                    if isinstance(issue, dict):
                        issues_summary += f"  - {issue.get('issue', 'Unknown issue')}\n"
                        if "element" in issue:
                            issues_summary += f"    Element: {issue['element']}\n"
                        if "id" in issue and issue["id"]:
                            issues_summary += f"    ID: #{issue['id']}\n"
                        if "class" in issue and issue["class"]:
                            issues_summary += f"    Class: .{issue['class']}\n"

        truncated_html = (
            html_content[:12000] if len(html_content) > 12000 else html_content
        )
        source_type = "Local HTML File" if content_type == "local_file" else "Webpage"

        prompt = f"""
Analyze this {source_type.lower()} for HTML alignment and layout issues and provide comprehensive CSS fixes.

**SOURCE:** {source}

**DETECTED ISSUES:**
{issues_summary if issues_summary else 'Initial scan complete - please analyze for alignment issues'}

**HTML CONTENT:**
```html
{truncated_html}
```

**EXISTING CSS:**
```css
{css_content if css_content else 'No existing CSS found'}
```

**ANALYSIS REQUIREMENTS:**

Please provide a comprehensive analysis with specific CSS fixes for alignment issues. Focus on:

1. **Layout Structure Issues:**
   - Broken flexbox/grid layouts
   - Misaligned containers and content
   - Poor spacing and margins
   - Float-based layouts that need modernization

2. **Responsive Design Problems:**
   - Fixed widths causing overflow
   - Missing mobile breakpoints
   - Unresponsive images and media

3. **Text and Content Alignment:**
   - Inconsistent text alignment
   - Poor typography spacing
   - Misaligned buttons and form elements

**OUTPUT FORMAT:**
Please provide your response in this exact format:

## ANALYSIS SUMMARY
[Brief overview of main issues found]

## CSS FIXES
```css
/* =================================== */
/* COMPREHENSIVE ALIGNMENT FIXES       */
/* =================================== */

/* 1. LAYOUT STRUCTURE FIXES */
[CSS rules for layout issues]

/* 2. RESPONSIVE DESIGN FIXES */
[CSS rules for responsive issues]

/* 3. TEXT AND CONTENT ALIGNMENT */
[CSS rules for text alignment]

/* 4. SPACING AND MARGIN CORRECTIONS */
[CSS rules for spacing issues]

/* 5. MODERN LAYOUT IMPROVEMENTS */
[CSS rules using flexbox/grid]
```

## EXPLANATION
[Detailed explanation of each fix and why it's needed]

**IMPORTANT:** 
- Use specific selectors that target the actual elements in the HTML
- Include complete CSS rule sets, not fragments
- Provide mobile-first responsive design with proper media queries
- Use modern CSS (flexbox, grid) instead of outdated methods
- Ensure all fixes are production-ready and cross-browser compatible

Please analyze the HTML thoroughly and provide comprehensive fixes that will significantly improve the layout and alignment.
"""
        return(prompt) 

    def normalize_file_path(self, path_or_url: str) -> str:
        """Normalize file path by handling URL encoding and file:// protocol"""
        if path_or_url.startswith("file://"):
            path_or_url = path_or_url[7:]
        decoded_path = unquote(path_or_url)
        if not os.path.isabs(decoded_path):
            decoded_path = os.path.abspath(decoded_path)
        return decoded_path

    def is_local_file(self, path_or_url: str) -> bool:
        """Determine if the input is a local file path or URL"""
        if path_or_url.startswith("file://"):
            return True
        if path_or_url.startswith(("http://", "https://", "ftp://")):
            return False
        try:
            normalized_path = self.normalize_file_path(path_or_url)
            return os.path.exists(normalized_path) and os.path.isfile(normalized_path)
        except:
            return False

    def create_working_copy(self, original_path: str) -> str:
        """Create a copy of the original file in the processing directory"""
        try:
            normalized_path = self.normalize_file_path(original_path)
            if not os.path.exists(normalized_path):
                raise FileNotFoundError(f"Source file not found: {normalized_path}")

            processing_dir = os.path.join(os.getcwd(), "processing")
            os.makedirs(processing_dir, exist_ok=True)

            original_name = os.path.basename(normalized_path)
            name, ext = os.path.splitext(original_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            working_copy_name = f"{name}_analysis_{timestamp}{ext}"

            working_copy_path = os.path.join(processing_dir, working_copy_name)
            shutil.copy2(normalized_path, working_copy_path)

            print(f"📁 Created working copy: {working_copy_path}")
            return working_copy_path

        except Exception as e:
            raise Exception(f"Error creating working copy: {str(e)}")

    def fetch_local_file_content(self, file_path: str) -> Dict[str, Any]:
        """Fetch local HTML file content for analysis"""
        try:
            normalized_path = self.normalize_file_path(file_path)
            if not os.path.exists(normalized_path):
                raise FileNotFoundError(f"File not found: {normalized_path}")

            working_copy_path = self.create_working_copy(normalized_path)

            with open(working_copy_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            file_info = os.stat(working_copy_path)

            return {
                "url": f"file://{normalized_path}",
                "original_path": normalized_path,
                "working_copy_path": working_copy_path,
                "file_name": os.path.basename(normalized_path),
                "file_size": file_info.st_size,
                "title": (
                    soup.title.string
                    if soup.title
                    else f"Local file: {os.path.basename(normalized_path)}"
                ),
                "html_content": html_content,
                "soup": soup,
                "content_type": "local_file",
            }

        except Exception as e:
            raise Exception(f"Error reading local file '{file_path}': {str(e)}")

    def fetch_webpage_content(self, url: str) -> Dict[str, Any]:
        """Fetch webpage content and save to processing folder"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            processing_dir = os.path.join(os.getcwd(), "processing")
            os.makedirs(processing_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain_name = urlparse(url).netloc.replace(".", "_")
            local_copy_name = f"webpage_{domain_name}_{timestamp}.html"
            local_copy_path = os.path.join(processing_dir, local_copy_name)

            with open(local_copy_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"📁 Created local copy in processing: {local_copy_path}")

            return {
                "url": url,
                "working_copy_path": local_copy_path,
                "title": soup.title.string if soup.title else "No title",
                "html_content": response.text,
                "soup": soup,
                "status_code": response.status_code,
                "content_type": "online_url",
            }
        except Exception as e:
            raise Exception(f"Error fetching webpage: {str(e)}")

    def fetch_content(self, path_or_url: str) -> Dict[str, Any]:
        """Unified method to fetch content from either local file or URL"""
        if self.is_local_file(path_or_url):
            print(f"📁 Detected local file: {path_or_url}")
            return self.fetch_local_file_content(path_or_url)
        else:
            print(f"🌐 Detected online URL: {path_or_url}")
            if not path_or_url.startswith(("http://", "https://")):
                path_or_url = "https://" + path_or_url
            return self.fetch_webpage_content(path_or_url)
# Usage example
    def get_prompt(self,path_or_url,results):
        page_data = self.fetch_content(path_or_url)
        css_content = ""
        style_tags = page_data["soup"].find_all("style")
        for style in style_tags[:2]:  # Only first 2 style tags
            if style.string:
                css_content += (
                    style.string[:2000] + "\n"
                )  # Limit to 2000 chars each

        analysis_prompt = self.create_bedrock_analysis_prompt(
                    path_or_url,
                    page_data["html_content"],
                    css_content,
                    results,
                    page_data["content_type"],
                )
        return(analysis_prompt)

    def call_bedrock_claude(self, prompt: str, max_tokens: int = 4000) -> str:
        """Make API call to Claude via AWS Bedrock"""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "top_p": 0.9,        
            }

            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
            )

            response_body = json.loads(response["body"].read())

            if "content" in response_body and len(response_body["content"]) > 0:
                return response_body["content"][0]["text"]
            else:
                return "No response content received from Bedrock"

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            raise Exception(f"Bedrock API error [{error_code}]: {error_message}")
        except Exception as e:
            raise Exception(f"Error calling Bedrock: {str(e)}")

    def extract_css_fixes_from_analysis(self, analysis_text: str) -> str:
        """Enhanced CSS extraction from Claude's analysis"""
        print("🔍 Extracting CSS fixes from analysis...")

        # Multiple patterns to catch different CSS block formats
        css_patterns = [
            r"```css\s*(.*?)\s*```",  # Standard CSS blocks
            r"```\s*css\s*(.*?)\s*```",  # CSS with extra spacing
            r"## CSS FIXES\s*```css\s*(.*?)\s*```",  # Specifically formatted blocks
            r"CSS FIXES.*?```css\s*(.*?)\s*```",  # Alternative formatting
        ]

        extracted_css = ""

        for pattern in css_patterns:
            matches = re.findall(pattern, analysis_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                clean_css = match.strip()
                if clean_css and len(clean_css) > 50:  # Only substantial CSS blocks
                    extracted_css += clean_css + "\n\n"

        # If no CSS found in code blocks, extract from the entire text
        if not extracted_css.strip():
            print("⚠️ No CSS blocks found, extracting CSS rules from text...")
            css_rules = re.findall(
                r"([.#]?[\w\-\s,]+)\s*\{([^}]+)\}",
                analysis_text,
                re.MULTILINE | re.DOTALL,
            )

            for selector, properties in css_rules:
                if len(properties.strip()) > 10:  # Only meaningful rules
                    extracted_css += (
                        f"{selector.strip()} {{\n{properties.strip()}\n}}\n\n"
                    )

        # Add comprehensive fallback fixes if extraction failed
        if not extracted_css.strip():
            print("⚠️ No CSS extracted, using comprehensive fallback fixes...")
            extracted_css = self.generate_comprehensive_fallback_css()

        print(f"✅ Extracted {len(extracted_css)} characters of CSS fixes")
        return extracted_css.strip()

    def generate_comprehensive_fallback_css(self) -> str:
        """Generate comprehensive fallback CSS fixes"""
        return """
/* =================================== */
/* COMPREHENSIVE ALIGNMENT FIXES       */
/* =================================== */

/* 1. RESET AND BASE STYLES */
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 0;
    line-height: 1.6;
}

/* 2. CONTAINER AND LAYOUT FIXES */
.container, .wrapper, .main-content, .content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
    width: 100%;
}

/* 3. FLEXBOX LAYOUT IMPROVEMENTS */
.row, .flex-container, .d-flex {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 20px;
}

.col, .column, .flex-item {
    flex: 1;
    min-width: 0;
}

/* 4. GRID LAYOUT IMPROVEMENTS */
.grid, .grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
}

/* 5. TEXT ALIGNMENT FIXES */
h1, h2, h3, h4, h5, h6 {
    margin: 0 0 1rem 0;
    line-height: 1.2;
}

p {
    margin: 0 0 1rem 0;
}

/* 6. IMAGE AND MEDIA RESPONSIVENESS */
img, video, iframe {
    max-width: 100%;
    height: auto;
    display: block;
}

/* 7. BUTTON AND FORM ALIGNMENT */
button, input, select, textarea {
    max-width: 100%;
    vertical-align: top;
}

.btn, button {
    display: inline-block;
    padding: 10px 20px;
    text-align: center;
    text-decoration: none;
    border: none;
    cursor: pointer;
}

/* 8. NAVIGATION FIXES */
nav ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
}

nav li {
    margin-right: 20px;
}

/* 9. FLOAT FIXES */
.clearfix::after {
    content: "";
    display: table;
    clear: both;
}

/* Remove floats in favor of flexbox */
.float-left, .float-right {
    float: none !important;
    display: inline-block;
}

/* 10. RESPONSIVE DESIGN */
@media (max-width: 768px) {
    .container, .wrapper, .main-content, .content {
        padding: 0 15px;
    }
    
    .row, .flex-container {
        flex-direction: column;
    }
    
    .col, .column {
        width: 100%;
        margin-bottom: 20px;
    }
    
    nav ul {
        flex-direction: column;
    }
    
    nav li {
        margin-right: 0;
        margin-bottom: 10px;
    }
}

@media (max-width: 480px) {
    .container, .wrapper, .main-content, .content {
        padding: 0 10px;
    }
    
    h1 { font-size: 1.8rem; }
    h2 { font-size: 1.5rem; }
    h3 { font-size: 1.3rem; }
}

/* 11. UTILITY CLASSES */
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }
.justify-center { justify-content: center; }
.align-center { align-items: center; }
.flex-column { flex-direction: column; }
.w-100 { width: 100%; }
.mb-0 { margin-bottom: 0; }
.mt-0 { margin-top: 0; }
"""

    def extract_and_apply_css_fixes(
        self, analysis_text: str, working_copy_path: str
    ) -> str:
        """Enhanced CSS extraction and application"""
        try:
            processing_dir = os.path.dirname(working_copy_path)

            # Read the working copy
            with open(working_copy_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")

            # Extract CSS fixes with improved method
            css_fixes = self.extract_css_fixes_from_analysis(analysis_text)

            if not css_fixes:
                print("⚠️ No CSS fixes extracted, generating fallback fixes")
                css_fixes = self.generate_comprehensive_fallback_css()

            # Apply fixes by injecting CSS into the HTML
            self._inject_css_fixes_enhanced(soup, css_fixes)

            # Create the fixed file name
            base_name = os.path.splitext(os.path.basename(working_copy_path))[0]
            fixed_file_path = os.path.join(processing_dir, f"{base_name}_FIXED.html")

            # Write the fixed HTML with proper formatting
            with open(fixed_file_path, "w", encoding="utf-8") as f:
                # Pretty print the HTML
                formatted_html = soup.prettify()
                f.write(formatted_html)

            print(f"🔧 Created enhanced fixed HTML file: {fixed_file_path}")

            # Create a separate CSS file as well
            css_file_path = os.path.join(processing_dir, f"{base_name}_fixes.css")
            with open(css_file_path, "w", encoding="utf-8") as f:
                f.write(css_fixes)
            print(f"📄 Created separate CSS file: {css_file_path}")

            return fixed_file_path

        except Exception as e:
            print(f"⚠️ Error applying CSS fixes: {str(e)}")
            return None

    def _inject_css_fixes_enhanced(self, soup: BeautifulSoup, css_fixes: str):
        """Enhanced CSS injection with better organization and viewport setup"""

        # Ensure we have a head element
        head = soup.find("head")
        if not head:
            if soup.html:
                head = soup.new_tag("head")
                soup.html.insert(0, head)
            else:
                # Create basic HTML structure if missing
                html_tag = soup.new_tag("html")
                head = soup.new_tag("head")
                body = soup.new_tag("body")

                # Move existing content to body
                for element in list(soup.children):
                    if element.name:
                        body.append(element.extract())

                html_tag.append(head)
                html_tag.append(body)
                soup.append(html_tag)

        # Add viewport meta tag if missing
        if not soup.find("meta", attrs={"name": "viewport"}):
            viewport_meta = soup.new_tag("meta")
            viewport_meta.attrs["name"] = "viewport"
            viewport_meta.attrs["content"] = "width=device-width, initial-scale=1.0"
            head.insert(0, viewport_meta)

        # Add charset meta if missing
        if not soup.find("meta", attrs={"charset": True}):
            charset_meta = soup.new_tag("meta")
            charset_meta.attrs["charset"] = "UTF-8"
            head.insert(0, charset_meta)

        # Create and inject the style tag with organized CSS
        style_tag = soup.new_tag("style")
        style_tag.attrs["type"] = "text/css"

        organized_css = f"""
/* ============================================ */
/* AUTOMATIC ALIGNMENT FIXES                    */
/* Generated by Enhanced HTML Alignment Agent  */
/* ============================================ */

{css_fixes}

/* ============================================ */
/* END OF AUTOMATIC FIXES                       */
/* ============================================ */
"""

        style_tag.string = organized_css

        # Insert the style tag (after existing styles if any)
        existing_styles = head.find_all("style")
        if existing_styles:
            existing_styles[-1].insert_after(style_tag)
        else:
            # Insert before any script tags, or at the end
            scripts = head.find_all("script")
            if scripts:
                scripts[0].insert_before(style_tag)
            else:
                head.append(style_tag)

        print("✅ Enhanced CSS fixes injected into HTML")

    async def analyze_with_bedrock(self, path_or_url: str) -> Dict[str, Any]:
        """Enhanced Bedrock analysis with improved fix application"""
        logger.info(f"Starting enhanced Bedrock analysis for: {path_or_url}")

        try:
            # Fetch content
            logger.info("Fetching content...")
            page_data = self.fetch_content(path_or_url)

            # Perform enhanced alignment analysis
            logger.info("Performing enhanced alignment analysis...")
            alignment_issues = await self.analyze_page_realtime(path_or_url)

            # Extract minimal CSS for context (not full CSS extraction)
            css_content = ""
            style_tags = page_data["soup"].find_all("style")
            for style in style_tags[:2]:  # Only first 2 style tags
                if style.string:
                    css_content += (
                        style.string[:2000] + "\n"
                    )  # Limit to 2000 chars each

            # Create analysis prompt
            logger.info("Creating comprehensive analysis prompt...")
            analysis_prompt =self.get_prompt(path_or_url, alignment_issues)

            # Call Bedrock for analysis
            logger.info("Calling Claude via AWS Bedrock...")
            bedrock_analysis = self.call_bedrock_claude(
                analysis_prompt, max_tokens=4000
            )

            # Apply fixes and create fixed HTML file
            fixed_file_path = None
            if "working_copy_path" in page_data:
                logger.info("Applying enhanced alignment fixes...")
                fixed_file_path = self.extract_and_apply_css_fixes(
                    bedrock_analysis, page_data["working_copy_path"]
                )

            result = {
                "source": path_or_url,
                "content_type": page_data["content_type"],
                "page_title": page_data["title"],
                "alignment_issues": alignment_issues,
                "css_content_length": len(css_content),
                "html_content_length": len(page_data["html_content"]),
                "bedrock_analysis": bedrock_analysis,
                "analysis_type": "enhanced_bedrock_claude_v2",
                "working_copy_path": page_data.get("working_copy_path"),
                "fixed_file_path": fixed_file_path,
                "processing_directory": os.path.join(os.getcwd(), "processing"),
            }

            if page_data["content_type"] == "local_file":
                result.update(
                    {
                        "original_path": page_data["original_path"],
                        "file_size": page_data["file_size"],
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error during Bedrock analysis: {str(e)}")
            return {"error": str(e), "source": path_or_url}

    def generate_analysis_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive analysis report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("HTML ALIGNMENT ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report_lines.append("")

        # Source information
        report_lines.append("SOURCE INFORMATION:")
        report_lines.append(f"  URL/Path: {results.get('source', 'Unknown')}")
        report_lines.append(f"  Content Type: {results.get('content_type', 'Unknown')}")
        report_lines.append(f"  Page Title: {results.get('page_title', 'Unknown')}")
        report_lines.append("")

        # Issues found
        alignment_issues = results.get("alignment_issues", {})
        total_issues = sum(len(issue_list) for issue_list in alignment_issues.values())
        report_lines.append(f"ISSUES DETECTED: {total_issues}")
        report_lines.append("")

        for category, issue_list in alignment_issues.items():
            if issue_list:
                category_name = category.replace("_", " ").title()
                report_lines.append(f"{category_name}: {len(issue_list)} issues")
                for issue in issue_list[:3]:  # Show first 3 issues
                    if isinstance(issue, dict):
                        report_lines.append(
                            f"  - {issue.get('issue', 'Unknown issue')}"
                        )
                        if issue.get("element"):
                            report_lines.append(f"    Element: {issue['element']}")
                report_lines.append("")

        # Processing information
        if results.get("working_copy_path"):
            report_lines.append("PROCESSING INFORMATION:")
            report_lines.append(f"  Working Copy: {results['working_copy_path']}")
            if results.get("fixed_file_path"):
                report_lines.append(f"  Fixed File: {results['fixed_file_path']}")
            report_lines.append(
                f"  Processing Directory: {results.get('processing_directory', 'N/A')}"
            )
            report_lines.append("")

        # Analysis details
        if results.get("bedrock_analysis"):
            report_lines.append("CLAUDE ANALYSIS:")
            report_lines.append("-" * 40)
            analysis_preview = results["bedrock_analysis"][:1000]
            if len(results["bedrock_analysis"]) > 1000:
                analysis_preview += "... [truncated for report]"
            report_lines.append(analysis_preview)
            report_lines.append("")

        # Error handling
        if results.get("error"):
            report_lines.append("ERROR:")
            report_lines.append(f"  {results['error']}")
            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_analysis_results(
        self, results: Dict[str, Any], output_dir: str = None
    ) -> str:
        """Save analysis results to files"""
        try:
            if output_dir is None:
                output_dir = os.path.join(os.getcwd(), "processing")

            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save detailed JSON results
            json_file_path = os.path.join(
                output_dir, f"analysis_results_{timestamp}.json"
            )
            json_safe_results = {k: v for k, v in results.items() if k != "soup"}
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(json_safe_results, f, indent=2, default=str)

            # Save human-readable report
            report_file_path = os.path.join(
                output_dir, f"analysis_report_{timestamp}.txt"
            )
            report_content = self.generate_analysis_report(results)
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            print(f"📊 Analysis results saved:")
            print(f"   JSON: {json_file_path}")
            print(f"   Report: {report_file_path}")

            return output_dir

        except Exception as e:
            print(f"⚠️ Error saving analysis results: {str(e)}")
            return None

    async def run_interactive_analysis(self):
        """Interactive mode for analysis"""
        print("\n" + "=" * 80)
        print("🔍 ENHANCED HTML ALIGNMENT ANALYSIS AGENT")
        print("=" * 80)
        print("This tool analyzes HTML files and webpages for alignment issues")
        print("and generates comprehensive CSS fixes using Claude AI.")
        print()

        while True:
            try:
                path_or_url = input(
                    "📎 Enter file path or URL (or 'quit' to exit): "
                ).strip()

                if path_or_url.lower() in ["quit", "exit", "q"]:
                    print("👋 Goodbye!")
                    break

                if not path_or_url:
                    print("⚠️ Please provide a valid file path or URL")
                    continue

                print(f"\n🚀 Starting analysis...")
                print("-" * 50)

                # Run the analysis
                results = await self.analyze_with_bedrock(path_or_url)

                if "error" in results:
                    print(f"❌ Error: {results['error']}")
                    continue

                # Display summary
                print("\n📋 ANALYSIS SUMMARY:")
                print(f"   Source: {results.get('source', 'Unknown')}")
                print(f"   Page Title: {results.get('page_title', 'Unknown')}")

                alignment_issues = results.get("alignment_issues", {})
                total_issues = sum(
                    len(issue_list) for issue_list in alignment_issues.values()
                )
                print(f"   Issues Found: {total_issues}")

                if results.get("fixed_file_path"):
                    print(f"   Fixed File: {results['fixed_file_path']}")

                # Save results
                self.save_analysis_results(results)

                print("\n✅ Analysis complete!")
                print("-" * 50)

            except KeyboardInterrupt:
                print("\n\n👋 Analysis interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {str(e)}")
                continue





async def main():
    parser = argparse.ArgumentParser(
        description="Enhanced HTML Alignment Analysis Agent with AWS Bedrock"
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="HTML file path or URL to analyze (optional for interactive mode)",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region for Bedrock (default: us-east-1)",
    )
    parser.add_argument("--profile", help="AWS profile name to use")
    parser.add_argument(
        "--cache-dir",
        default=".cache",
        help="Cache directory for storing temporary files",
    )
    parser.add_argument("--output-dir", help="Output directory for analysis results")
    parser.add_argument(
        "--interactive", action="store_true", help="Run in interactive mode"
    )

    args = parser.parse_args()

    try:
        analyzer = RealTimeCSSAnalyzer(
            region_name=args.region,
            profile_name=args.profile,
            cache_dir=args.cache_dir,
        )

        if args.interactive or not args.source:
            await analyzer.run_interactive_analysis()
        else:
            # Use the command line argument instead of hardcoded path
            path_or_url = args.source
            results = await analyzer.analyze_with_bedrock(path_or_url)
            output_dir = analyzer.save_analysis_results(results, args.output_dir)

            print("\n✅ Analysis complete!")
            if output_dir:
                print(f"📁 Results saved to: {output_dir}")

            if results.get("fixed_file_path"):
                print(f"🔧 Fixed HTML file: {results['fixed_file_path']}")

    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())