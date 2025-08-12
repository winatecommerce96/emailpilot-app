// Development Login Component for Local Testing
const DevLogin = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [email, setEmail] = React.useState('damon@winatecommerce.com');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [success, setSuccess] = React.useState(false);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/admin/dev-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email })
      });
      
      if (response.ok) {
        const data = await response.json();
        setSuccess(true);
        setTimeout(() => {
          window.location.reload(); // Reload to update app state
        }, 1500);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Login failed');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Check if already logged in
  React.useEffect(() => {
    fetch('/api/auth/session', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        if (data.authenticated) {
          setSuccess(true);
        }
      })
      .catch(() => {});
  }, []);

  // Don't show button if already logged in
  if (success && !isOpen) {
    return null;
  }

  return React.createElement(React.Fragment, null,
    // Login Button
    !success && React.createElement('button', {
      onClick: () => setIsOpen(true),
      style: {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        background: 'linear-gradient(135deg, #f59e0b, #dc2626)',
        color: 'white',
        border: 'none',
        padding: '12px 24px',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
        zIndex: 999,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
      }
    }, '🔐 Dev Login'),

    // Login Modal
    isOpen && React.createElement('div', {
      style: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.5)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      },
      onClick: () => !loading && setIsOpen(false)
    },
      React.createElement('div', {
        style: {
          background: 'white',
          width: '90%',
          maxWidth: '400px',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
        },
        onClick: e => e.stopPropagation()
      },
        // Header
        React.createElement('div', {
          style: {
            background: 'linear-gradient(135deg, #f59e0b, #dc2626)',
            color: 'white',
            padding: '20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }
        },
          React.createElement('h2', { style: { margin: 0, fontSize: '20px' } }, '🔐 Development Login'),
          React.createElement('button', {
            onClick: () => setIsOpen(false),
            disabled: loading,
            style: {
              background: 'none',
              border: 'none',
              color: 'white',
              fontSize: '24px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.5 : 1
            }
          }, '×')
        ),

        // Content
        React.createElement('div', { style: { padding: '20px' } },
          success ? 
            React.createElement('div', {
              style: {
                textAlign: 'center',
                padding: '20px'
              }
            },
              React.createElement('div', {
                style: {
                  fontSize: '48px',
                  marginBottom: '10px'
                }
              }, '✅'),
              React.createElement('p', {
                style: {
                  fontSize: '18px',
                  color: '#16a34a',
                  fontWeight: '600'
                }
              }, 'Login Successful!'),
              React.createElement('p', {
                style: {
                  fontSize: '14px',
                  color: '#6b7280',
                  marginTop: '10px'
                }
              }, 'Redirecting...')
            ) :
          React.createElement('div', null,
            React.createElement('p', {
              style: {
                fontSize: '14px',
                color: '#6b7280',
                marginBottom: '20px'
              }
            }, 'This is for local development only. Select an approved email to access admin features.'),
            
            React.createElement('label', {
              style: {
                display: 'block',
                marginBottom: '5px',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151'
              }
            }, 'Email Address'),
            
            React.createElement('select', {
              value: email,
              onChange: (e) => setEmail(e.target.value),
              disabled: loading,
              style: {
                width: '100%',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                fontSize: '14px',
                marginBottom: '20px',
                cursor: loading ? 'not-allowed' : 'pointer'
              }
            },
              React.createElement('option', { value: 'damon@winatecommerce.com' }, 'damon@winatecommerce.com'),
              React.createElement('option', { value: 'admin@emailpilot.ai' }, 'admin@emailpilot.ai')
            ),
            
            error && React.createElement('div', {
              style: {
                background: '#fee2e2',
                border: '1px solid #fca5a5',
                borderRadius: '6px',
                padding: '10px',
                marginBottom: '20px',
                fontSize: '14px',
                color: '#dc2626'
              }
            }, error),
            
            React.createElement('button', {
              onClick: handleLogin,
              disabled: loading,
              style: {
                width: '100%',
                background: loading ? '#9ca3af' : 'linear-gradient(135deg, #f59e0b, #dc2626)',
                color: 'white',
                border: 'none',
                padding: '12px',
                borderRadius: '6px',
                fontSize: '16px',
                fontWeight: '600',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s'
              }
            }, loading ? 'Logging in...' : 'Login'),
            
            React.createElement('p', {
              style: {
                fontSize: '12px',
                color: '#9ca3af',
                marginTop: '15px',
                textAlign: 'center'
              }
            }, '⚠️ This login method is disabled in production')
          )
        )
      )
    )
  );
};

// Export for use in app
window.DevLogin = DevLogin;