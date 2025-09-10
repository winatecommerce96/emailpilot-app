/**
 * Modern Login Component with Clerk/Multi-tenant Support
 */

function LoginV2() {
    const { login, register, loginWithClerk, loginWithGoogle, error: authError, loading } = useAuthV2();
    
    const [mode, setMode] = React.useState('login'); // 'login', 'register', 'tenant'
    const [formData, setFormData] = React.useState({
        email: '',
        password: '',
        name: '',
        company: '',
        tenantId: ''
    });
    const [error, setError] = React.useState('');
    const [success, setSuccess] = React.useState('');
    const [showPassword, setShowPassword] = React.useState(false);

    // Clear messages when mode changes
    React.useEffect(() => {
        setError('');
        setSuccess('');
    }, [mode]);

    // Handle form input changes
    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    // Handle form submission
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        try {
            if (mode === 'login') {
                await login(formData.email, formData.password, formData.tenantId || null);
                setSuccess('Login successful!');
                // Redirect after short delay
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else if (mode === 'register') {
                await register(
                    formData.email,
                    formData.password,
                    formData.name,
                    formData.company || null,
                    formData.tenantId || null
                );
                setSuccess('Registration successful! Redirecting...');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            }
        } catch (err) {
            setError(err.message || 'An error occurred');
        }
    };

    // Demo login for testing
    const handleDemoLogin = async () => {
        try {
            await login('demo@emailpilot.ai', 'demo');
            setSuccess('Demo login successful!');
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } catch (err) {
            setError('Demo login failed');
        }
    };

    return React.createElement('div', {
        className: 'min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8'
    },
        React.createElement('div', {
            className: 'max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-lg'
        },
            // Header
            React.createElement('div', null,
                React.createElement('h2', {
                    className: 'mt-6 text-center text-3xl font-extrabold text-gray-900'
                },
                    mode === 'login' ? 'Sign in to EmailPilot' :
                    mode === 'register' ? 'Create your account' :
                    'Select your organization'
                ),
                React.createElement('p', {
                    className: 'mt-2 text-center text-sm text-gray-600'
                },
                    'Modern authentication with multi-tenant support'
                )
            ),

            // SSO Options
            React.createElement('div', {
                className: 'space-y-3'
            },
                // Clerk SSO
                React.createElement('button', {
                    onClick: loginWithClerk,
                    className: 'w-full flex justify-center items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500',
                    disabled: loading
                },
                    React.createElement('svg', {
                        className: 'w-5 h-5 mr-2',
                        fill: 'currentColor',
                        viewBox: '0 0 20 20'
                    },
                        React.createElement('path', {
                            d: 'M10 2a8 8 0 100 16 8 8 0 000-16zM8 12a1 1 0 11-2 0V9a1 1 0 112 0v3zm4 0a1 1 0 11-2 0V9a1 1 0 112 0v3z'
                        })
                    ),
                    'Continue with Clerk SSO'
                ),

                // Google OAuth (legacy)
                React.createElement('button', {
                    onClick: loginWithGoogle,
                    className: 'w-full flex justify-center items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500',
                    disabled: loading
                },
                    React.createElement('svg', {
                        className: 'w-5 h-5 mr-2',
                        viewBox: '0 0 24 24'
                    },
                        React.createElement('path', {
                            fill: '#4285F4',
                            d: 'M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z'
                        }),
                        React.createElement('path', {
                            fill: '#34A853',
                            d: 'M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z'
                        }),
                        React.createElement('path', {
                            fill: '#FBBC05',
                            d: 'M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z'
                        }),
                        React.createElement('path', {
                            fill: '#EA4335',
                            d: 'M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z'
                        })
                    ),
                    'Continue with Google'
                ),

                // Demo Login
                React.createElement('button', {
                    onClick: handleDemoLogin,
                    className: 'w-full flex justify-center items-center px-4 py-2 border border-blue-300 rounded-md shadow-sm text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
                    disabled: loading
                },
                    '🎭 Try Demo Account'
                )
            ),

            // Divider
            React.createElement('div', {
                className: 'relative'
            },
                React.createElement('div', {
                    className: 'absolute inset-0 flex items-center'
                },
                    React.createElement('div', {
                        className: 'w-full border-t border-gray-300'
                    })
                ),
                React.createElement('div', {
                    className: 'relative flex justify-center text-sm'
                },
                    React.createElement('span', {
                        className: 'px-2 bg-white text-gray-500'
                    }, 'Or continue with email')
                )
            ),

            // Form
            React.createElement('form', {
                className: 'mt-8 space-y-6',
                onSubmit: handleSubmit
            },
                React.createElement('div', {
                    className: 'space-y-4'
                },
                    // Email field
                    React.createElement('div', null,
                        React.createElement('label', {
                            htmlFor: 'email',
                            className: 'block text-sm font-medium text-gray-700'
                        }, 'Email address'),
                        React.createElement('input', {
                            id: 'email',
                            name: 'email',
                            type: 'email',
                            autoComplete: 'email',
                            required: true,
                            value: formData.email,
                            onChange: handleChange,
                            className: 'mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
                            placeholder: 'you@example.com'
                        })
                    ),

                    // Password field
                    React.createElement('div', null,
                        React.createElement('label', {
                            htmlFor: 'password',
                            className: 'block text-sm font-medium text-gray-700'
                        }, 'Password'),
                        React.createElement('div', {
                            className: 'mt-1 relative'
                        },
                            React.createElement('input', {
                                id: 'password',
                                name: 'password',
                                type: showPassword ? 'text' : 'password',
                                autoComplete: mode === 'login' ? 'current-password' : 'new-password',
                                required: true,
                                value: formData.password,
                                onChange: handleChange,
                                className: 'appearance-none relative block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
                                placeholder: '••••••••'
                            }),
                            React.createElement('button', {
                                type: 'button',
                                onClick: () => setShowPassword(!showPassword),
                                className: 'absolute inset-y-0 right-0 pr-3 flex items-center'
                            },
                                React.createElement('svg', {
                                    className: 'h-5 w-5 text-gray-400',
                                    fill: 'none',
                                    viewBox: '0 0 24 24',
                                    stroke: 'currentColor'
                                },
                                    showPassword ?
                                    React.createElement('path', {
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                        strokeWidth: 2,
                                        d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z'
                                    }) :
                                    React.createElement('path', {
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                        strokeWidth: 2,
                                        d: 'M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21'
                                    })
                                )
                            )
                        )
                    ),

                    // Additional fields for registration
                    mode === 'register' && React.createElement(React.Fragment, null,
                        // Name field
                        React.createElement('div', null,
                            React.createElement('label', {
                                htmlFor: 'name',
                                className: 'block text-sm font-medium text-gray-700'
                            }, 'Full Name'),
                            React.createElement('input', {
                                id: 'name',
                                name: 'name',
                                type: 'text',
                                autoComplete: 'name',
                                required: mode === 'register',
                                value: formData.name,
                                onChange: handleChange,
                                className: 'mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
                                placeholder: 'John Doe'
                            })
                        ),

                        // Company field
                        React.createElement('div', null,
                            React.createElement('label', {
                                htmlFor: 'company',
                                className: 'block text-sm font-medium text-gray-700'
                            }, 'Company (Optional)'),
                            React.createElement('input', {
                                id: 'company',
                                name: 'company',
                                type: 'text',
                                autoComplete: 'organization',
                                value: formData.company,
                                onChange: handleChange,
                                className: 'mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
                                placeholder: 'Acme Inc.'
                            })
                        )
                    ),

                    // Tenant ID field (optional)
                    React.createElement('div', null,
                        React.createElement('label', {
                            htmlFor: 'tenantId',
                            className: 'block text-sm font-medium text-gray-700'
                        }, 'Organization ID (Optional)'),
                        React.createElement('input', {
                            id: 'tenantId',
                            name: 'tenantId',
                            type: 'text',
                            value: formData.tenantId,
                            onChange: handleChange,
                            className: 'mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
                            placeholder: 'Leave empty for personal account'
                        })
                    )
                ),

                // Error message
                error && React.createElement('div', {
                    className: 'rounded-md bg-red-50 p-4'
                },
                    React.createElement('div', {
                        className: 'flex'
                    },
                        React.createElement('div', {
                            className: 'flex-shrink-0'
                        },
                            React.createElement('svg', {
                                className: 'h-5 w-5 text-red-400',
                                fill: 'currentColor',
                                viewBox: '0 0 20 20'
                            },
                                React.createElement('path', {
                                    fillRule: 'evenodd',
                                    d: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z',
                                    clipRule: 'evenodd'
                                })
                            )
                        ),
                        React.createElement('div', {
                            className: 'ml-3'
                        },
                            React.createElement('p', {
                                className: 'text-sm text-red-800'
                            }, error)
                        )
                    )
                ),

                // Success message
                success && React.createElement('div', {
                    className: 'rounded-md bg-green-50 p-4'
                },
                    React.createElement('div', {
                        className: 'flex'
                    },
                        React.createElement('div', {
                            className: 'flex-shrink-0'
                        },
                            React.createElement('svg', {
                                className: 'h-5 w-5 text-green-400',
                                fill: 'currentColor',
                                viewBox: '0 0 20 20'
                            },
                                React.createElement('path', {
                                    fillRule: 'evenodd',
                                    d: 'M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z',
                                    clipRule: 'evenodd'
                                })
                            )
                        ),
                        React.createElement('div', {
                            className: 'ml-3'
                        },
                            React.createElement('p', {
                                className: 'text-sm text-green-800'
                            }, success)
                        )
                    )
                ),

                // Submit button
                React.createElement('div', null,
                    React.createElement('button', {
                        type: 'submit',
                        disabled: loading,
                        className: 'group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed'
                    },
                        loading ? 'Processing...' :
                        mode === 'login' ? 'Sign in' :
                        'Create account'
                    )
                )
            ),

            // Mode toggle
            React.createElement('div', {
                className: 'text-center'
            },
                React.createElement('button', {
                    type: 'button',
                    onClick: () => setMode(mode === 'login' ? 'register' : 'login'),
                    className: 'text-sm text-indigo-600 hover:text-indigo-500'
                },
                    mode === 'login' 
                        ? "Don't have an account? Sign up"
                        : 'Already have an account? Sign in'
                )
            )
        )
    );
}

// Export for use
window.LoginV2 = LoginV2;