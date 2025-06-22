# import streamlit as st
# import pandas as pd
# import plotly.express as px

# class PortfolioVisualization:
#     def create_portfolio_visualization(self, portfolio_data):
#         """Create comprehensive interactive portfolio visualizations"""
#         if not portfolio_data['holdings']:
#             st.info("📊 No investments to visualize yet. Start investing to see your portfolio analytics!")
#             return

#         holdings_df = pd.DataFrame(portfolio_data['holdings'])

#         # Create tabs for different visualizations
#         viz_tabs = st.tabs([
#             "💰 Portfolio Overview",
#             "📊 Performance Analysis",
#             "🎯 Asset Allocation",
#             "📈 Risk Analysis",
#             "🌳 Portfolio Treemap",
#             "📉 Individual Analysis"
#         ])

#         with viz_tabs[0]:  # Portfolio Overview
#             col1, col2, col3, col4 = st.columns(4)

#             with col1:
#                 st.metric(
#                     "Total Invested",
#                     f"₹{portfolio_data['total_invested']:,.0f}"
#                 )

#             with col2:
#                 st.metric(
#                     "Current Value",
#                     f"₹{portfolio_data['total_current_value']:,.0f}",
#                     f"₹{portfolio_data['total_current_value'] - portfolio_data['total_invested']:,.0f}"
#                 )

#             with col3:
#                 st.metric(
#                     "Total Return",
#                     f"{portfolio_data['portfolio_return']:.2f}%"
#                 )

#             with col4:
#                 avg_holding_period = holdings_df['days_held'].mean()
#                 st.metric(
#                     "Avg Holding Period",
#                     f"{avg_holding_period:.0f} days"
#                 )

#             # Portfolio composition donut chart
#             st.subheader("Portfolio Composition")
#             fig_donut = px.pie(
#                 holdings_df,
#                 values='current_value',
#                 names='name',
#                 hole=0.4,
#                 title="Current Portfolio Value Distribution"
#             )
#             fig_donut.update_traces(textposition='inside', textinfo='percent+label')
#             st.plotly_chart(fig_donut, use_container_width=True)

#         with viz_tabs[1]:  # Performance Analysis
#             st.subheader("📊 Performance Analysis")

#             # Performance bar chart
#             fig_perf = px.bar(
#                 holdings_df.sort_values('gain_loss_pct', ascending=True),
#                 x='gain_loss_pct',
#                 y='name',
#                 orientation='h',
#                 title="Investment Performance (%)",
#                 color='gain_loss_pct',
#                 color_continuous_scale='RdYlGn',
#                 text='gain_loss_pct'
#             )
#             fig_perf.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
#             fig_perf.update_layout(height=400)
#             st.plotly_chart(fig_perf, use_container_width=True)

#             # Scatter plot: Risk vs Return
#             st.subheader("Risk vs Return Analysis")
#             fig_scatter = px.scatter(
#                 holdings_df,
#                 x='volatility',
#                 y='gain_loss_pct',
#                 size='current_value',
#                 color='asset_type',
#                 hover_data=['name', 'invested', 'current_value'],
#                 title="Risk vs Return (Bubble size = Current Value)",
#                 labels={'volatility': 'Volatility (%)', 'gain_loss_pct': 'Return (%)'}
#             )
#             st.plotly_chart(fig_scatter, use_container_width=True)

#             # Momentum analysis
#             st.subheader("30-Day Momentum Analysis")
#             fig_momentum = px.bar(
#                 holdings_df.sort_values('momentum_30d', ascending=True),
#                 x='momentum_30d',
#                 y='name',
#                 orientation='h',
#                 title="30-Day Price Momentum (%)",
#                 color='momentum_30d',
#                 color_continuous_scale='RdYlGn'
#             )
#             fig_momentum.update_layout(height=400)
#             st.plotly_chart(fig_momentum, use_container_width=True)

#         with viz_tabs[2]:  # Asset Allocation
#             st.subheader("🎯 Asset Allocation Analysis")

#             # Asset allocation pie chart
#             asset_allocation = holdings_df.groupby('asset_type')['current_value'].sum().reset_index()

#             col1, col2 = st.columns(2)

#             with col1:
#                 fig_pie = px.pie(
#                     asset_allocation,
#                     values='current_value',
#                     names='asset_type',
#                     title="Asset Allocation by Value"
#                 )
#                 st.plotly_chart(fig_pie, use_container_width=True)

#             with col2:
#                 # Asset allocation table
#                 asset_allocation['percentage'] = (asset_allocation['current_value'] / asset_allocation['current_value'].sum()) * 100
#                 asset_allocation['current_value_formatted'] = asset_allocation['current_value'].apply(lambda x: f"₹{x:,.0f}")
#                 asset_allocation['percentage_formatted'] = asset_allocation['percentage'].apply(lambda x: f"{x:.1f}%")

#                 st.dataframe(
#                     asset_allocation[['asset_type', 'current_value_formatted', 'percentage_formatted']].rename(columns={
#                         'asset_type': 'Asset Type',
#                         'current_value_formatted': 'Value',
#                         'percentage_formatted': 'Percentage'
#                     }),
#                     use_container_width=True
#                 )

#             # Sunburst chart for hierarchical view
#             st.subheader("Hierarchical Portfolio View")
#             fig_sunburst = px.sunburst(
#                 holdings_df,
#                 path=['asset_type', 'name'],
#                 values='current_value',
#                 title="Portfolio Hierarchy - Asset Type → Individual Holdings"
#             )
#             st.plotly_chart(fig_sunburst, use_container_width=True)

#         with viz_tabs[3]:  # Risk Analysis
#             st.subheader("⚠️ Risk Analysis Dashboard")

#             # Risk metrics
#             col1, col2, col3 = st.columns(3)

#             with col1:
#                 avg_volatility = holdings_df['volatility'].mean()
#                 st.metric("Avg Portfolio Volatility", f"{avg_volatility:.2f}%")

#             with col2:
#                 max_exposure = holdings_df['current_value'].max()
#                 max_exposure_pct = (max_exposure / portfolio_data['total_current_value']) * 100
#                 st.metric("Max Single Exposure", f"{max_exposure_pct:.1f}%")

#             with col3:
#                 diversification_ratio = len(holdings_df) / (holdings_df['current_value'].std() / holdings_df['current_value'].mean())
#                 st.metric("Diversification Score", f"{diversification_ratio:.2f}")

#             # Volatility distribution
#             fig_vol = px.histogram(
#                 holdings_df,
#                 x='volatility',
#                 title="Volatility Distribution of Holdings",
#                 nbins=20,
#                 labels={'volatility': 'Volatility (%)', 'count': 'Number of Holdings'}
#             )
#             st.plotly_chart(fig_vol, use_container_width=True)

#             # Risk heatmap
#             risk_matrix = holdings_df.pivot_table(
#                 values='current_value',
#                 index='asset_type',
#                 columns=pd.cut(holdings_df['volatility'], bins=3, labels=['Low Risk', 'Medium Risk', 'High Risk']),
#                 aggfunc='sum',
#                 fill_value=0
#             )

#             fig_heatmap = px.imshow(
#                 risk_matrix.values,
#                 x=risk_matrix.columns,
#                 y=risk_matrix.index,
#                 aspect="auto",
#                 title="Risk Distribution Heatmap (Value in ₹)"
#             )
#             st.plotly_chart(fig_heatmap, use_container_width=True)

#         with viz_tabs[4]:  # Portfolio Treemap
#             st.subheader("🌳 Portfolio Treemap")

#             # Create treemap
#             fig_treemap = px.treemap(
#                 holdings_df,
#                 path=[px.Constant("Portfolio"), 'asset_type', 'name'],
#                 values='current_value',
#                 color='gain_loss_pct',
#                 color_continuous_scale='RdYlGn',
#                 title="Portfolio Treemap - Size by Value, Color by Performance"
#             )
#             fig_treemap.update_layout(height=600)
#             st.plotly_chart(fig_treemap, use_container_width=True)

#             # Alternative treemap by volatility
#             fig_treemap_vol = px.treemap(
#                 holdings_df,
#                 path=[px.Constant("Portfolio"), 'asset_type', 'name'],
#                 values='current_value',
#                 color='volatility',
#                 color_continuous_scale='Reds',
#                 title="Portfolio Treemap - Size by Value, Color by Volatility"
#             )
#             fig_treemap_vol.update_layout(height=600)
#             st.plotly_chart(fig_treemap_vol, use_container_width=True)

#         with viz_tabs[5]:  # Individual Analysis
#             st.subheader("📉 Individual Stock/Fund Analysis")

#             # Dropdown to select individual holding
#             selected_holding = st.selectbox(
#                 "Select a holding for detailed analysis:",
#                 options=holdings_df['name'].tolist(),
#                 format_func=lambda x: f"{x} ({holdings_df[holdings_df['name']==x]['symbol'].iloc[0]})"
#             )

#             if selected_holding:
#                 holding_data = holdings_df[holdings_df['name'] == selected_holding].iloc[0].to_dict()

#                 # Display key metrics
#                 col1, col2, col3, col4 = st.columns(4)

#                 with col1:
#                     st.metric("Current Price", f"₹{holding_data['current_price']:.2f}")

#                 with col2:
#                     st.metric("Purchase Price", f"₹{holding_data['purchase_price']:.2f}")

#                 with col3:
#                     st.metric("Return", f"{holding_data['gain_loss_pct']:.2f}%")

#                 with col4:
#                     st.metric("Volatility", f"{holding_data['volatility']:.2f}%")

#                 # Create detailed chart
#                 detailed_chart = self.create_individual_stock_chart(holding_data)
#                 if detailed_chart:
#                     st.plotly_chart(detailed_chart, use_container_width=True)

#                 # Additional metrics table
#                 st.subheader("Detailed Metrics")
#                 metrics_data = {
#                     "Metric": [
#                         "Investment Amount", "Current Value", "Gain/Loss", "Quantity",
#                         "Days Held", "6-Month High", "6-Month Low", "30-Day Momentum"
#                     ],
#                     "Value": [
#                         f"₹{holding_data['invested']:,.2f}",
#                         f"₹{holding_data['current_value']:,.2f}",
#                         f"₹{holding_data['gain_loss']:,.2f}",
#                         f"{holding_data['quantity']:.2f}",
#                         f"{holding_data['days_held']} days",
#                         f"₹{holding_data['max_price_6mo']:.2f}",
#                         f"₹{holding_data['min_price_6mo']:.2f}",
#                         f"{holding_data['momentum_30d']:.2f}%"
#                     ]
#                 }

#                 metrics_df = pd.DataFrame(metrics_data)
#                 st.dataframe(metrics_df, use_container_width=True, hide_index=True)
