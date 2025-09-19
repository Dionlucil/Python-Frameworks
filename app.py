import streamlit as st
import pandas as pd
import os

# Configure page
st.set_page_config(page_title="CORD-19 Explorer", layout="wide")

# Cache the data loading function
@st.cache_data
def load_sample_data(nrows=10000):
    """Load a sample of the dataset for faster processing"""
    try:
        pd.read_csv("metadata.csv", nrows=nrows, low_memory=False)
        return df
    except Exception as e:
        st.error(f"Error loading dataset: {e}")
        return None

@st.cache_data
def get_dataset_info():
    """Get basic info about the dataset without loading it fully"""
    try:
        # Get file size
        file_path = "metadata.csv/metadata.csv"
        file_size = os.path.getsize(file_path) / (1024 * 1024 * 1024)  # Size in GB
        
        # Get column names without loading full data
        df_sample = pd.read_csv(file_path, nrows=0)
        columns = df_sample.columns.tolist()
        
        return file_size, columns
    except Exception as e:
        return None, None

# Sidebar for data loading options
st.sidebar.title("Data Loading Options")

# Get dataset info
file_size, columns = get_dataset_info()
if file_size:
    st.sidebar.info(f"Dataset size: {file_size:.2f} GB")
    st.sidebar.info(f"Columns: {len(columns)}")

# Choose loading mode
load_mode = st.sidebar.selectbox(
    "Choose data loading mode:",
    ["Sample (10K rows) - Fast", "Sample (50K rows) - Medium", "Full dataset - Slow"]
)

# Load data based on selection
with st.spinner("Loading dataset..."):
    if load_mode == "Sample (10K rows) - Fast":
        df = load_sample_data(10000)
    elif load_mode == "Sample (50K rows) - Medium":
        df = load_sample_data(50000)
    else:
        # For full dataset, use chunking
        try:
            chunks = []
            chunk_size = 50000
            total_rows = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for chunk in pd.read_csv("metadata.csv/metadata.csv", chunksize=chunk_size, low_memory=False):
                chunks.append(chunk)
                total_rows += len(chunk)
                
                # Update progress
                progress_bar.progress(min(total_rows / 1000000, 1.0))  # Assume max 1M rows for progress
                status_text.text(f"Loaded {total_rows:,} rows...")
                
                # Safety limit to prevent memory issues
                if total_rows >= 500000:  # Limit to 500K rows max
                    st.warning("Limited to 500,000 rows to prevent memory issues")
                    break
            
            if chunks:
                df = pd.concat(chunks, ignore_index=True)
                progress_bar.empty()
                status_text.empty()
            else:
                st.error("No data loaded")
                st.stop()
                
        except Exception as e:
            st.error(f"Error loading full dataset: {e}")
            st.info("Falling back to sample data...")
            df = load_sample_data(10000)

if df is None:
    st.error("Failed to load dataset")
    st.stop()

# Main content
st.title("CORD-19 Dataset Explorer")
st.success(f"✅ Loaded {len(df):,} rows successfully!")

# Dataset info
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Rows", f"{len(df):,}")
with col2:
    st.metric("Columns", len(df.columns))
with col3:
    st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

# Show sample data
with st.expander("📋 View Sample Data", expanded=False):
    st.dataframe(df.head(10))

# Data preparation with progress
st.subheader("🔧 Preparing Data")
with st.spinner("Processing data..."):
    # Handle missing columns gracefully
    if "publish_time" in df.columns:
        df["publish_time"] = pd.to_datetime(df["publish_time"], errors="coerce")
        df = df.dropna(subset=["publish_time"])
        df["year"] = df["publish_time"].dt.year
    else:
        st.warning("'publish_time' column not found. Using available data.")
        df["year"] = 2020  # Default year if column missing

# Filtering section
st.subheader("🎛️ Data Filtering")

# Year range filter
if "year" in df.columns and not df["year"].isna().all():
    min_year, max_year = int(df["year"].min()), int(df["year"].max())
    year_range = st.slider("Select year range:", min_year, max_year, (2020, 2021))
    filtered = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]
else:
    filtered = df
    st.info("No year data available for filtering")

# Visualizations
st.subheader("📊 Visualizations")

# Create two columns for charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Publications by Year")
    if "year" in filtered.columns and not filtered["year"].isna().all():
        year_counts = filtered["year"].value_counts().sort_index()
        st.bar_chart(year_counts)
    else:
        st.info("No year data available for chart")

with col2:
    st.subheader("📰 Top 10 Journals")
    if "journal" in filtered.columns:
        top_journals = filtered["journal"].value_counts().head(10)
        st.bar_chart(top_journals)
    else:
        st.info("No journal data available")

# Additional insights
st.subheader("📋 Data Insights")

# Show column information
with st.expander("📊 Column Information"):
    try:
        # Create column info safely
        col_info_data = {
            'Column': df.columns.tolist(),
            'Data Type': [str(dtype) for dtype in df.dtypes],
            'Non-Null Count': df.count().tolist(),
            'Null Count': df.isnull().sum().tolist(),
            'Memory Usage (KB)': (df.memory_usage(deep=True) / 1024).tolist()
        }
        
        # Ensure all arrays have the same length
        max_len = len(df.columns)
        for key, values in col_info_data.items():
            if len(values) != max_len:
                col_info_data[key] = values[:max_len] if len(values) > max_len else values + [0] * (max_len - len(values))
        
        col_info = pd.DataFrame(col_info_data)
        st.dataframe(col_info)
    except Exception as e:
        st.error(f"Error creating column information: {e}")
        # Fallback: show basic column info
        st.write("**Available Columns:**")
        for i, col in enumerate(df.columns):
            st.write(f"{i+1}. {col} ({df[col].dtype})")

# Show filtered data
with st.expander(f"🔍 Filtered Data ({len(filtered):,} rows)"):
    st.dataframe(filtered.head(20))
