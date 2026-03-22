# HTML Real-Time CSS Analysis Tool

A powerful Python tool that performs comprehensive real-time analysis of HTML files and web pages to detect layout issues, then uses AI (Claude via AWS Bedrock) to generate professional CSS fixes.

## 🚀 Features

### Real-Time Browser Analysis
- Uses Playwright to launch actual browsers for accurate rendering analysis
- Tests across multiple viewport sizes (desktop, tablet, mobile)
- Analyzes computed styles, not just source code

### Comprehensive Issue Detection
The tool detects 8 categories of layout and CSS issues:
- **Computed Style Issues**: Zero-dimension elements, conflicting positioning
- **Layout Geometry**: Overlapping elements, extreme margins
- **Responsive Design**: Overflow issues, touch target sizes
- **Performance Issues**: Layout thrashing, expensive CSS properties
- **Visual Problems**: Hidden elements, distorted images
- **Accessibility**: Missing focus indicators, contrast issues
- **Dynamic Behavior**: Layout stability during interactions
- **Cross-Browser Issues**: Browser-specific CSS compatibility

### AI-Powered CSS Fixes
- Integrates with Anthropic's Claude via AWS Bedrock
- Generates comprehensive, production-ready CSS fixes
- Creates both corrected HTML files and separate CSS files

## 📋 Requirements

- Python 3.8+
- AWS Account with Bedrock access
- AWS CLI configured with credentials

### Example Output

The tool generates:
- **Fixed HTML files** with applied CSS corrections
- **Analysis reports** (`.txt`) with detailed findings
- **JSON results** (`.json`) for programmatic use
- **Separate CSS files** (`.css`) with the fixes

## 🔧 How It Works

1. **Content Fetching**: Downloads or reads the target HTML file
2. **Real-Time Analysis**: Launches browser and analyzes actual rendered layout
3. **Issue Detection**: Scans for 40+ types of layout and CSS problems
4. **AI Analysis**: Sends findings to Claude for intelligent CSS fix generation
5. **Fix Application**: Injects generated CSS into HTML and creates output files

## 📁 Output Structure

```
processing/
├── analysis_results_20260322_202317.json    # Detailed JSON results
├── analysis_report_20260322_202317.txt      # Human-readable report
├── yourfile_analysis_20260322_202317.html   # Working copy
├── yourfile_analysis_20260322_202317_FIXED.html  # Fixed HTML
└── yourfile_fixes.css                       # CSS fixes
```

## ⚙️ Configuration

### AWS Bedrock Model
The tool uses Claude 3.5 Sonnet. Update the model ID in the code if needed:
```python
self.model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
```

### Environment Variables
Create a .env file for configuration:
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

## 🐛 Troubleshooting

### Common Issues

1. **"Cannot navigate to invalid URL"**
   - Fixed in v1.1: URL normalization for local files

2. **"Access denied" on Bedrock**
   - Model may be legacy - upgrade to newer Claude model
   - Check AWS credentials and permissions

3. **Playwright browser launch fails**
   - Run: `playwright install`
   - Check system dependencies

4. **AWS Region issues**
   - Ensure Bedrock is available in your region
   - Default: us-east-1
---

**Note**: This tool requires active AWS Bedrock access and may incur costs for API usage.
```
