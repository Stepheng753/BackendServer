from flask import url_for, render_template


def render_endpoints(app):
    """
    Renders a welcome page with a list of all available endpoints.
    """
    endpoints_data = []
    # Iterate over all registered URL rules in the application
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        # We don't need to show the static endpoint
        if rule.endpoint != 'static':
            # Get the HTTP methods allowed for the endpoint, excluding HEAD and OPTIONS for brevity
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))

            # Create a dictionary for each endpoint to pass to the template
            endpoints_data.append({
                'rule': rule.rule,
                'url': url_for(rule.endpoint, _external=True),
                'methods': methods
            })

    return render_template(
        'index.html',
        title="Flash Server",
        favicon_url=url_for('static', filename='flash.png'),
        image_url=url_for('static', filename='flash.gif'),
        endpoints=endpoints_data
    )
