import streamlit as st
import json
import pandas as pd

# Load the JSON data
with open('metadata/ec2_instance_types.json') as f:
    data = json.load(f)

# Flatten the nested data into a table format
def create_dataframe(data):
    records = []
    zones = ['a', 'b', 'c', 'd', 'e', 'f']  # Up to Zone F

    for region, families in data.items():
        for family, instance_types in families.items():
            for instance_type, availability_zones in instance_types.items():
                # Default to "❌" for each zone
                availability = {zone: "❌" for zone in zones}

                # Mark available zones with "✅"
                for az in availability_zones:
                    if az in availability:
                        availability[az] = "✅"

                # Add the row to records
                row = {
                    'Region': region,
                    'Family': family,
                    'Instance Type': instance_type,
                    **availability
                }
                records.append(row)

    return pd.DataFrame(records)

# Create the DataFrame from the JSON data
df = create_dataframe(data)

# Define styling function for the DataFrame - only center alignment
def style_instance_matrix(df):
    return df.style.set_properties(**{'text-align': 'center'})

# Streamlit UI setup
st.title('AWS EC2 Zonal Support Matrix')

# Sidebar filters
st.sidebar.header("Filters")

# Region filter (default is 'us-east-1')
regions_selected = st.sidebar.multiselect(
    'Select Regions',
    df['Region'].unique(),
    default=['us-east-1']  # Default selection is only 'us-east-1'
)

# Family filter
family_filter = st.sidebar.selectbox(
    'Select Instance Family',
    ['All'] + sorted(df['Family'].unique().tolist())
)

# Instance Type filter logic - changes based on family selection
if family_filter == 'All':
    # If "All" is selected for family, disable instance type selection
    instance_type_filter = 'All'
    st.sidebar.selectbox(
        'Select Instance Type',
        ['All'],
        disabled=True
    )
else:
    # If a specific family is selected, show its instance types
    instance_type_filter = st.sidebar.selectbox(
        'Select Instance Type',
        ['All'] + sorted(df[df['Family'] == family_filter]['Instance Type'].unique().tolist())
    )

# Filter data based on user input
if family_filter == 'All':
    # Show all families for selected regions
    filtered_df = df[df['Region'].isin(regions_selected)]
elif instance_type_filter == 'All':
    # Show all instance types for selected family and regions
    filtered_df = df[(df['Region'].isin(regions_selected)) & (df['Family'] == family_filter)]
else:
    # Show specific instance type for selected family and regions
    filtered_df = df[(df['Region'].isin(regions_selected)) & 
                     (df['Family'] == family_filter) & 
                     (df['Instance Type'] == instance_type_filter)]

# Display the styled DataFrame without the index (line number)
styled_filtered_df = filtered_df.set_index(['Region', 'Family', 'Instance Type'])
st.dataframe(style_instance_matrix(styled_filtered_df), use_container_width=True)

# Display the full table (optional, can be toggled)
if st.sidebar.checkbox('Show full table', False):
    st.subheader('Full EC2 Instance Availability Matrix')
    styled_full_df = df.set_index(['Region', 'Family', 'Instance Type'])
    st.dataframe(style_instance_matrix(styled_full_df), use_container_width=True)
