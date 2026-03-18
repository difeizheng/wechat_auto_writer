#!/bin/bash
echo "正在启动公众号文章自动生成器..."
echo "访问地址：http://localhost:8601"
streamlit run app/main.py --server.port=8601