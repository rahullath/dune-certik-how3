from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from app import app, db
from models import Protocol, Score, RevenueData, UserData
from data_processor import DataProcessor

# Add current date to all templates for copyright year
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/')
def index():
    """Home page showing top protocols by How3 score."""
    # Check if we have any protocols
    has_data = db.session.query(Protocol).first() is not None
    
    if has_data:
        # Get top protocols by How3 score
        top_protocols = (db.session.query(Protocol, Score)
            .join(Score, Protocol.id == Score.protocol_id)
            .order_by(desc(Score.how3_score))
            .limit(10)
            .all())
        
        # Get top protocols by category
        categories = db.session.query(Protocol.category, func.count(Protocol.id)).group_by(Protocol.category).all()
        
        category_leaders = {}
        for category, _ in categories:
            leader = (db.session.query(Protocol, Score)
                .join(Score, Protocol.id == Score.protocol_id)
                .filter(Protocol.category == category)
                .order_by(desc(Score.how3_score))
                .first())
            if leader:
                category_leaders[category] = leader
    else:
        # No data yet
        top_protocols = []
        category_leaders = {}
    
    return render_template('index.html', 
                           top_protocols=top_protocols, 
                           category_leaders=category_leaders,
                           has_data=has_data)

@app.route('/protocols')
def protocols():
    """List all protocols with their scores."""
    # Check if we have any protocols
    has_data = db.session.query(Protocol).first() is not None
    
    if has_data:
        category = request.args.get('category', '')
        sort_by = request.args.get('sort', 'how3_score')
        order = request.args.get('order', 'desc')
        
        # Base query
        query = db.session.query(Protocol, Score).join(Score, Protocol.id == Score.protocol_id)
        
        # Apply category filter if specified
        if category:
            query = query.filter(Protocol.category == category)
        
        # Apply sorting
        if sort_by == 'how3_score':
            order_col = desc(Score.how3_score) if order == 'desc' else Score.how3_score
        elif sort_by == 'eqs':
            order_col = desc(Score.eqs) if order == 'desc' else Score.eqs
        elif sort_by == 'ugs':
            order_col = desc(Score.ugs) if order == 'desc' else Score.ugs
        elif sort_by == 'fvs':
            order_col = desc(Score.fvs) if order == 'desc' else Score.fvs
        elif sort_by == 'ss':
            order_col = desc(Score.ss) if order == 'desc' else Score.ss
        elif sort_by == 'name':
            order_col = desc(Protocol.name) if order == 'desc' else Protocol.name
        else:
            order_col = desc(Score.how3_score)
        
        query = query.order_by(order_col)
        
        protocols = query.all()
        categories = db.session.query(Protocol.category).distinct().all()
        categories = [c[0] for c in categories]
    else:
        # No data yet
        protocols = []
        categories = []
        category = ''
        sort_by = 'how3_score'
        order = 'desc'
    
    return render_template('protocols.html', 
                           protocols=protocols, 
                           categories=categories,
                           current_category=category,
                           current_sort=sort_by,
                           current_order=order,
                           has_data=has_data)

@app.route('/protocol/<int:protocol_id>')
def protocol_detail(protocol_id):
    """Show detailed information for a specific protocol."""
    protocol = Protocol.query.get_or_404(protocol_id)
    scores = Score.query.filter_by(protocol_id=protocol_id).order_by(Score.calculated_at.desc()).first()
    
    # Get historical data for charts
    today = datetime.utcnow().date()
    start_date = today - relativedelta(months=12)
    
    revenue_data = (RevenueData.query
        .filter(RevenueData.protocol_id == protocol_id, RevenueData.month >= start_date)
        .order_by(RevenueData.month)
        .all())
    
    user_data = (UserData.query
        .filter(UserData.protocol_id == protocol_id, UserData.month >= start_date)
        .order_by(UserData.month)
        .all())
    
    # Prepare chart data
    revenue_chart_data = {
        'labels': [data.month.strftime('%b %Y') for data in revenue_data if data.source == revenue_data[0].source],
        'datasets': []
    }
    
    # Group revenue data by source
    sources = set(data.source for data in revenue_data)
    for source in sources:
        source_data = [data for data in revenue_data if data.source == source]
        if source_data:
            revenue_chart_data['datasets'].append({
                'label': source,
                'data': [data.total_fees for data in source_data]
            })
    
    user_chart_data = {
        'labels': [data.month.strftime('%b %Y') for data in user_data],
        'active_addresses': [data.active_addresses for data in user_data],
        'transaction_count': [data.transaction_count for data in user_data],
        'transaction_volume': [data.transaction_volume for data in user_data]
    }
    
    # Get protocols in the same category for comparison
    similar_protocols = (db.session.query(Protocol, Score)
        .join(Score, Protocol.id == Score.protocol_id)
        .filter(Protocol.category == protocol.category, Protocol.id != protocol_id)
        .order_by(desc(Score.how3_score))
        .limit(5)
        .all())
    
    return render_template('protocol_detail.html',
                           protocol=protocol,
                           scores=scores,
                           revenue_chart_data=revenue_chart_data,
                           user_chart_data=user_chart_data,
                           similar_protocols=similar_protocols)

@app.route('/compare')
def compare_protocols():
    """Compare multiple protocols."""
    # Check if we have any protocols
    has_data = db.session.query(Protocol).first() is not None
    
    if not has_data:
        flash('No protocols available for comparison', 'warning')
        return redirect(url_for('protocols'))
    
    protocol_ids = request.args.getlist('ids[]')
    
    if not protocol_ids:
        flash('Please select protocols to compare', 'warning')
        return redirect(url_for('protocols'))
    
    protocols_data = []
    for protocol_id in protocol_ids:
        protocol = Protocol.query.get(protocol_id)
        if protocol:
            score = Score.query.filter_by(protocol_id=protocol_id).order_by(Score.calculated_at.desc()).first()
            if score:
                protocols_data.append({
                    'protocol': protocol,
                    'score': score
                })
    
    # All available protocols for the select inputs
    all_protocols = Protocol.query.order_by(Protocol.name).all()
    
    return render_template('compare.html',
                           protocols_data=protocols_data,
                           all_protocols=all_protocols)

@app.route('/api/protocols')
def api_protocols():
    """API endpoint to get all protocols with their scores."""
    # Check if we have any protocols
    has_data = db.session.query(Protocol).first() is not None
    
    if has_data:
        # Get protocol data with scores
        protocols = db.session.query(Protocol, Score).join(Score, Protocol.id == Score.protocol_id).all()
        
        result = []
        for protocol, score in protocols:
            result.append({
                'id': protocol.id,
                'name': protocol.name,
                'symbol': protocol.symbol,
                'category': protocol.category,
                'market_cap': protocol.market_cap,
                'annual_revenue': protocol.annual_revenue,
                'scores': {
                    'how3_score': score.how3_score,
                    'eqs': score.eqs,
                    'ugs': score.ugs,
                    'fvs': score.fvs,
                    'ss': score.ss,
                    'calculated_at': score.calculated_at.isoformat()
                }
            })
    else:
        # No data yet
        result = []
    
    return jsonify(result)

@app.route('/api/protocol/<int:protocol_id>')
def api_protocol_detail(protocol_id):
    """API endpoint to get detailed information for a specific protocol."""
    protocol = Protocol.query.get_or_404(protocol_id)
    score = Score.query.filter_by(protocol_id=protocol_id).order_by(Score.calculated_at.desc()).first()
    
    # Get historical data
    today = datetime.utcnow().date()
    start_date = today - relativedelta(months=12)
    
    revenue_data = RevenueData.query.filter(
        RevenueData.protocol_id == protocol_id,
        RevenueData.month >= start_date
    ).order_by(RevenueData.month).all()
    
    user_data = UserData.query.filter(
        UserData.protocol_id == protocol_id,
        UserData.month >= start_date
    ).order_by(UserData.month).all()
    
    # Format response
    result = {
        'protocol': {
            'id': protocol.id,
            'name': protocol.name,
            'symbol': protocol.symbol,
            'category': protocol.category,
            'description': protocol.description,
            'market_cap': protocol.market_cap,
            'annual_revenue': protocol.annual_revenue
        },
        'scores': {
            'how3_score': score.how3_score,
            'eqs': score.eqs,
            'ugs': score.ugs,
            'fvs': score.fvs,
            'ss': score.ss,
            'calculated_at': score.calculated_at.isoformat()
        },
        'revenue_data': [
            {
                'month': data.month.isoformat(),
                'total_fees': data.total_fees,
                'source': data.source,
                'mom_change': data.mom_change
            }
            for data in revenue_data
        ],
        'user_data': [
            {
                'month': data.month.isoformat(),
                'active_addresses': data.active_addresses,
                'transaction_count': data.transaction_count,
                'transaction_volume': data.transaction_volume,
                'active_address_growth_rate': data.active_address_growth_rate,
                'transaction_count_growth_rate': data.transaction_count_growth_rate,
                'transaction_volume_growth_rate': data.transaction_volume_growth_rate
            }
            for data in user_data
        ]
    }
    
    return jsonify(result)

@app.route('/api/update/<int:protocol_id>', methods=['POST'])
def api_update_protocol(protocol_id):
    """API endpoint to trigger a data update for a specific protocol."""
    processor = DataProcessor()
    success = processor.update_protocol_data(protocol_id)
    
    if success:
        return jsonify({'status': 'success', 'message': 'Protocol data updated successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update protocol data'}), 500

@app.route('/api/categories')
def api_categories():
    """API endpoint to get all protocol categories with counts."""
    # Check if we have any protocols
    has_data = db.session.query(Protocol).first() is not None
    
    if has_data:
        categories = db.session.query(
            Protocol.category, 
            func.count(Protocol.id).label('count')
        ).group_by(Protocol.category).all()
        
        result = [
            {
                'name': category,
                'count': count
            }
            for category, count in categories
        ]
    else:
        # No data yet
        result = []
    
    return jsonify(result)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
