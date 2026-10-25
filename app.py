"""
Flask Application for Traffic Accident Hotspot Visualization

This application visualizes accident hotspots from cleaned accident data
using interactive Folium heatmaps with optional filtering by State and Month.

Author: Data Engineering Assignment Extension
"""

from flask import Flask, render_template, request
import pandas as pd
import folium
from folium.plugins import HeatMap
import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))

# Path to the cleaned dataset
DATA_FILE = os.path.join(BASE_DIR, 'data', 'cleaned_accidents.csv')


def load_data():
    """
    Load the cleaned accidents dataset.
    Returns a pandas DataFrame with the accident data.
    """
    try:
        # Load CSV - don't specify dtypes for State/Month in case they don't exist
        # We'll handle missing columns gracefully
        df = pd.read_csv(
            DATA_FILE,
            dtype={
                'Severity': 'int8',
                'Start_Lat': 'float32',
                'Start_Lng': 'float32'
            },
            low_memory=False
        )
        
        # Ensure we have valid coordinates
        df = df.dropna(subset=['Start_Lat', 'Start_Lng'])
        
        # Filter out any invalid coordinates (safety check)
        df = df[
            (df['Start_Lat'].between(-90, 90)) &
            (df['Start_Lng'].between(-180, 180))
        ]
        
        # Check if State column exists, if not create a dummy one
        if 'State' not in df.columns:
            print("⚠️  Warning: 'State' column not found in CSV. Creating placeholder.")
            df['State'] = 'Unknown'
        
        # Check if Month column exists, if not try to extract from Start_Time
        if 'Month' not in df.columns:
            print("⚠️  Warning: 'Month' column not found in CSV. Attempting to extract from Start_Time.")
            if 'Start_Time' in df.columns:
                try:
                    df['Start_Time'] = pd.to_datetime(df['Start_Time'], errors='coerce')
                    df['Month'] = df['Start_Time'].dt.month
                    print("✓ Successfully extracted Month from Start_Time")
                except Exception as e:
                    print(f"⚠️  Could not extract Month: {e}")
                    df['Month'] = 1  # Default to January
            else:
                print("⚠️  Start_Time column also not found. Setting Month to 1.")
                df['Month'] = 1
        
        # Ensure State and Month are proper types
        if 'State' in df.columns:
            df['State'] = df['State'].astype(str)
        if 'Month' in df.columns:
            df['Month'] = df['Month'].astype('int8')
        
        return df
    except FileNotFoundError:
        print(f"Error: Could not find {DATA_FILE}")
        print("Please ensure cleaned_accidents.csv is in the data/ directory")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def filter_data(df, state=None, month=None):
    """
    Filter the dataset based on selected State and Month.
    
    Args:
        df: pandas DataFrame with accident data
        state: State code to filter by (e.g., 'CA', 'TX')
        month: Month number to filter by (1-12)
    
    Returns:
        Filtered pandas DataFrame
    """
    filtered_df = df.copy()
    
    # Filter by state if provided and column exists
    if state and state != 'All' and 'State' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['State'] == state]
    
    # Filter by month if provided and column exists
    if month and month != 'All' and 'Month' in filtered_df.columns:
        # Convert month to integer if it's a string
        month_int = int(month) if isinstance(month, str) else month
        filtered_df = filtered_df[filtered_df['Month'] == month_int]
    
    return filtered_df


def create_heatmap(df, sample_size=10000):
    """
    Create a Folium heatmap from accident data.
    
    Args:
        df: pandas DataFrame with Start_Lat and Start_Lng columns
        sample_size: Maximum number of points to display (for performance)
    
    Returns:
        Folium Map object with heatmap layer
    """
    # Sample data if too large (for performance)
    if len(df) > sample_size:
        df_sample = df.sample(n=sample_size, random_state=42)
    else:
        df_sample = df
    
    # Calculate map center (mean of coordinates)
    if len(df_sample) == 0:
        # Default center (US center) if no data
        center_lat, center_lng = 39.8283, -98.5795
    else:
        center_lat = df_sample['Start_Lat'].mean()
        center_lng = df_sample['Start_Lng'].mean()
    
    # Create base map
    accident_map = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=5,
        tiles='OpenStreetMap'
    )
    
    # Prepare heatmap data: list of [lat, lng] pairs
    heat_data = [
        [row['Start_Lat'], row['Start_Lng']]
        for idx, row in df_sample.iterrows()
        if pd.notna(row['Start_Lat']) and pd.notna(row['Start_Lng'])
    ]
    
    # Add heatmap layer
    if len(heat_data) > 0:
        HeatMap(
            heat_data,
            radius=15,
            blur=10,
            max_zoom=18,
            min_opacity=0.4
        ).add_to(accident_map)
    
    return accident_map


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route: Display the accident hotspot map with optional filters.
    """
    # Load the full dataset
    df = load_data()
    
    # Get filter values from form submission
    selected_state = request.form.get('state', 'All')
    selected_month = request.form.get('month', 'All')
    
    # If no form submission, use GET parameters (for initial load)
    if request.method == 'GET':
        selected_state = request.args.get('state', 'All')
        selected_month = request.args.get('month', 'All')
    
    # Filter data based on selections
    filtered_df = filter_data(df, selected_state, selected_month)
    
    # Create heatmap
    accident_map = create_heatmap(filtered_df)
    
    # State code to full name mapping
    state_names = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
    }
    
    # Get unique states and months for dropdowns (handle missing columns gracefully)
    if 'State' in df.columns:
        state_codes = sorted(df['State'].dropna().unique().tolist())
        # Create list of tuples: (state_code, state_full_name) for dropdown
        # Format: ('All', 'All States') or ('CA', 'California')
        states_list = [('All', 'All States')]
        for code in state_codes:
            full_name = state_names.get(code.upper(), code)  # Use code if mapping not found
            states_list.append((code, full_name))
        states = states_list
    else:
        states = [('All', 'All States')]
        print("⚠️  State column not available - state filter disabled")
    
    if 'Month' in df.columns:
        months = ['All'] + [str(i) for i in sorted(df['Month'].dropna().unique().tolist())]
    else:
        months = ['All']
        print("⚠️  Month column not available - month filter disabled")
    
    # Month names for display
    month_names = {
        '1': 'January', '2': 'February', '3': 'March', '4': 'April',
        '5': 'May', '6': 'June', '7': 'July', '8': 'August',
        '9': 'September', '10': 'October', '11': 'November', '12': 'December'
    }
    
    # Convert map to HTML
    map_html = accident_map._repr_html_()
    
    # Statistics for display
    total_accidents = len(filtered_df)
    total_all = len(df)
    
    return render_template(
        'index.html',
        map_html=map_html,
        states=states,
        months=months,
        month_names=month_names,
        state_names=state_names,  # Pass state mapping to template
        selected_state=selected_state,
        selected_month=selected_month,
        total_accidents=total_accidents,
        total_all=total_all
    )


if __name__ == '__main__':
    # Check if data file exists
    if not os.path.exists(DATA_FILE):
        print(f"\n⚠️  WARNING: {DATA_FILE} not found!")
        print("Please ensure cleaned_accidents.csv is in the data/ directory\n")
    
    # Run the Flask app
    print("\n🚀 Starting Flask application...")
    print("📊 Accident Hotspot Visualization Dashboard")
    print("🌐 Open your browser and navigate to: http://127.0.0.1:5000\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
