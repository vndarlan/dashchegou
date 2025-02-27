FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port Streamlit will run on
EXPOSE 8501

# Command to run the application
CMD streamlit run Home.py --server.port=$PORT --server.address=0.0.0.0