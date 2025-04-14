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
family_filter = st.sidebar.selectbox('Select Instance Family', df['Family'].unique())

# Instance Type filter (show all by default)
instance_type_filter = st.sidebar.selectbox(
    'Select Instance Type',
    ['All'] + [instance_type for instance_type in df[df['Family'] == family_filter]['Instance Type'].unique()]
)

# Filter data based on user input
if instance_type_filter == 'All':
    filtered_df = df[(df['Region'].isin(regions_selected)) & (df['Family'] == family_filter)]
else:
    filtered_df = df[(df['Region'].isin(regions_selected)) & 
                     (df['Family'] == family_filter) & 
                     (df['Instance Type'] == instance_type_filter)]

# Display the filtered DataFrame without the index (line number)
st.dataframe(filtered_df.set_index(['Region', 'Family', 'Instance Type']), use_container_width=True)

# Display the full table (optional, can be toggled)
if st.sidebar.checkbox('Show full table', False):
    st.subheader('Full EC2 Instance Availability Matrix')
    st.dataframe(df.set_index(['Region', 'Family', 'Instance Type']), use_container_width=True)

# Add spacer to push the button to the bottom
for _ in range(10):
    st.sidebar.write("")
