import logging
from flask import render_template, request, jsonify, flash, redirect, url_for
from sqlalchemy import desc
from models import Protocol, Score, Category, RevenueData, UserData
from app import db
from data_processor import DataProcessor
from score_calculator import ScoreCalculator

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all routes with the Flask app"""
    
    @app.route('/')
    def index():
        """Home page with top protocols by How3 score"""
        top_protocols = db.session.query(Protocol, Score) \
            .join(Score, Protocol.id == Score.protocol_id) \
            .order_by(desc(Score.how3_score)) \
            .limit(10) \
            .all()
            
        categories = Category.query.all()
        
        return render_template('index.html', 
                              protocols=top_protocols,
                              categories=categories)
    
    @app.route('/protocols')
    def protocols():
        """List all protocols with their scores"""
        category_filter = request.args.get('category')
        sort_by = request.args.get('sort_by', 'how3_score')
        sort_order = request.args.get('sort_order', 'desc')
        
        query = db.session.query(Protocol, Score) \
            .join(Score, Protocol.id == Score.protocol_id)
            
        if category_filter:
            query = query.filter(Protocol.category == category_filter)
        
        # Apply sorting
        if sort_by == 'earnings_quality_score':
            query = query.order_by(desc(Score.earnings_quality_score) if sort_order == 'desc' else Score.earnings_quality_score)
        elif sort_by == 'user_growth_score':
            query = query.order_by(desc(Score.user_growth_score) if sort_order == 'desc' else Score.user_growth_score)
        elif sort_by == 'fair_value_score':
            query = query.order_by(desc(Score.fair_value_score) if sort_order == 'desc' else Score.fair_value_score)
        elif sort_by == 'safety_score':
            query = query.order_by(desc(Score.safety_score) if sort_order == 'desc' else Score.safety_score)
        else:  # Default to how3_score
            query = query.order_by(desc(Score.how3_score) if sort_order == 'desc' else Score.how3_score)
        
        protocols = query.all()
        categories = Category.query.all()
        
        return render_template('protocols.html',
                              protocols=protocols,
                              categories=categories,
                              selected_category=category_filter,
                              sort_by=sort_by,
                              sort_order=sort_order)
    
    @app.route('/protocol/<int:protocol_id>')
    def protocol_detail(protocol_id):
        """Detailed view for a specific protocol"""
        protocol = Protocol.query.get_or_404(protocol_id)
        score = Score.query.filter_by(protocol_id=protocol_id).first()
        
        # Get historical revenue data
        revenue_data = RevenueData.query.filter_by(protocol_id=protocol_id) \
            .order_by(RevenueData.month) \
            .all()
            
        # Get historical user data
        user_data = UserData.query.filter_by(protocol_id=protocol_id) \
            .order_by(UserData.month) \
            .all()
            
        # Get category peers for comparison
        category_peers = db.session.query(Protocol, Score) \
            .join(Score, Protocol.id == Score.protocol_id) \
            .filter(Protocol.category == protocol.category) \
            .filter(Protocol.id != protocol_id) \
            .order_by(desc(Score.how3_score)) \
            .limit(5) \
            .all()
        
        return render_template('protocol.html',
                              protocol=protocol,
                              score=score,
                              revenue_data=revenue_data,
                              user_data=user_data,
                              category_peers=category_peers)
    
    @app.route('/categories')
    def categories():
        """View all protocol categories with average scores"""
        categories = Category.query.all()
        
        category_data = []
        for category in categories:
            # Calculate average scores for each category
            protocols = db.session.query(Protocol, Score) \
                .join(Score, Protocol.id == Score.protocol_id) \
                .filter(Protocol.category == category.name) \
                .all()
                
            if protocols:
                avg_eqs = sum(score.earnings_quality_score for _, score in protocols) / len(protocols)
                avg_ugs = sum(score.user_growth_score for _, score in protocols) / len(protocols)
                avg_fvs = sum(score.fair_value_score for _, score in protocols) / len(protocols)
                avg_ss = sum(score.safety_score for _, score in protocols) / len(protocols)
                avg_how3 = sum(score.how3_score for _, score in protocols) / len(protocols)
                
                category_data.append({
                    'category': category,
                    'protocol_count': len(protocols),
                    'avg_eqs': avg_eqs,
                    'avg_ugs': avg_ugs,
                    'avg_fvs': avg_fvs,
                    'avg_ss': avg_ss,
                    'avg_how3': avg_how3
                })
            else:
                category_data.append({
                    'category': category,
                    'protocol_count': 0,
                    'avg_eqs': 0,
                    'avg_ugs': 0,
                    'avg_fvs': 0,
                    'avg_ss': 0,
                    'avg_how3': 0
                })
        
        return render_template('categories.html', category_data=category_data)
    
    @app.route('/about')
    def about():
        """About page with methodology explanation"""
        return render_template('about.html')
    
    # API endpoint for chart data
    @app.route('/api/protocol/<int:protocol_id>/revenue-history')
    def api_revenue_history(protocol_id):
        """API endpoint for protocol revenue history"""
        protocol = Protocol.query.get_or_404(protocol_id)
        
        revenue_data = RevenueData.query.filter_by(protocol_id=protocol_id) \
            .order_by(RevenueData.month) \
            .all()
            
        data = [{
            'month': rd.month.strftime('%Y-%m'),
            'revenue': rd.revenue,
            'source': rd.revenue_source
        } for rd in revenue_data]
        
        return jsonify(data)
    
    @app.route('/api/protocol/<int:protocol_id>/user-history')
    def api_user_history(protocol_id):
        """API endpoint for protocol user history"""
        protocol = Protocol.query.get_or_404(protocol_id)
        
        user_data = UserData.query.filter_by(protocol_id=protocol_id) \
            .order_by(UserData.month) \
            .all()
            
        data = [{
            'month': ud.month.strftime('%Y-%m'),
            'active_addresses': ud.active_addresses,
            'transaction_count': ud.transaction_count,
            'transaction_volume': ud.transaction_volume,
            'active_address_growth': ud.active_address_growth,
            'transaction_count_growth': ud.transaction_count_growth,
            'transaction_volume_growth': ud.transaction_volume_growth,
            'active_address_percentile': ud.active_address_percentile,
            'transaction_count_percentile': ud.transaction_count_percentile,
            'transaction_volume_percentile': ud.transaction_volume_percentile
        } for ud in user_data]
        
        return jsonify(data)
    
    # Manual update trigger endpoint (can be protected by auth in production)
    @app.route('/admin/update-data', methods=['POST'])
    def admin_update_data():
        """Manually trigger data updates"""
        try:
            protocol_id = request.form.get('protocol_id')
            
            data_processor = DataProcessor()
            score_calculator = ScoreCalculator()
            
            if protocol_id:
                protocol = Protocol.query.get_or_404(int(protocol_id))
                
                success_revenue = data_processor.process_revenue_data(protocol.name)
                success_user = data_processor.process_user_data(protocol.name)
                
                if success_revenue and success_user:
                    score_calculator.calculate_protocol_scores(protocol_id=protocol.id)
                    flash(f"Successfully updated data for {protocol.name}", "success")
                else:
                    flash(f"Error updating data for {protocol.name}", "danger")
            else:
                # Update all protocols
                success_count = data_processor.update_all_protocols()
                score_calculator.calculate_protocol_scores()
                flash(f"Successfully updated data for {success_count} protocols", "success")
            
            return redirect(request.referrer or url_for('index'))
            
        except Exception as e:
            logger.error(f"Error in admin update: {str(e)}")
            flash(f"Error: {str(e)}", "danger")
            return redirect(request.referrer or url_for('index'))
