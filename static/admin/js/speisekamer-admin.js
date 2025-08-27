// Speisekamer Kitchen Catalog Admin JavaScript

(function($) {
    'use strict';

    // DOM Ready
    $(document).ready(function() {
        initializeSpeisekamarAdmin();
    });

    function initializeSpeisekamarAdmin() {
        enhanceImagePreviews();
        addLoadingStates();
        improveFormValidation();
        addKeyboardShortcuts();
        enhanceStockDisplays();
        addAutoSave();
        improveSearch();
        addConfirmDialogs();
        enhancePriceFields();
        addDashboardAnimations();
    }

    // Enhanced Image Previews
    function enhanceImagePreviews() {
        $('.file-upload input[type="file"]').on('change', function() {
            const file = this.files[0];
            const $container = $(this).closest('.form-group');
            
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Remove existing preview
                    $container.find('.image-preview').remove();
                    
                    // Create new preview
                    const $preview = $(`
                        <div class="image-preview mt-3">
                            <img src="${e.target.result}" 
                                 class="product-image-preview" 
                                 alt="Preview">
                            <div class="image-info mt-2">
                                <small class="text-muted">
                                    ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)
                                </small>
                            </div>
                        </div>
                    `);
                    
                    $container.append($preview);
                    
                    // Add click to zoom functionality
                    $preview.find('img').on('click', function() {
                        showImageModal(e.target.result, file.name);
                    });
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Image Modal for Zoom
    function showImageModal(src, filename) {
        const modal = $(`
            <div class="modal fade" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${filename}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="${src}" class="img-fluid" alt="${filename}">
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(modal);
        modal.modal('show');
        modal.on('hidden.bs.modal', function() {
            modal.remove();
        });
    }

    // Loading States
    function addLoadingStates() {
        // Form submissions
        $('form').on('submit', function() {
            const $form = $(this);
            const $submitBtn = $form.find('input[type="submit"], button[type="submit"]');
            
            // Show loading overlay
            showLoadingOverlay();
            
            // Disable submit button and change text
            $submitBtn.prop('disabled', true)
                     .addClass('btn-loading')
                     .data('original-text', $submitBtn.val() || $submitBtn.text())
                     .val('Saving...')
                     .text('Saving...');
        });

        // AJAX requests
        $(document).ajaxStart(function() {
            showLoadingOverlay();
        }).ajaxStop(function() {
            hideLoadingOverlay();
        });
    }

    function showLoadingOverlay() {
        if (!$('.loading-overlay').length) {
            $('body').append(`
                <div class="loading-overlay">
                    <div class="loading-spinner"></div>
                </div>
            `);
        }
    }

    function hideLoadingOverlay() {
        $('.loading-overlay').fadeOut(300, function() {
            $(this).remove();
        });
    }

    // Enhanced Form Validation
    function improveFormValidation() {
        // Real-time validation for material codes
        $('input[name*="material_code"]').on('input', function() {
            const $input = $(this);
            const value = $input.val().toUpperCase();
            
            // Auto-format material code
            $input.val(value);
            
            // Validate format (e.g., ABC-DEF-123)
            const isValid = /^[A-Z]{2,4}-[A-Z]{2,4}-\d{3}(-[A-Z]{2})?$/.test(value);
            
            if (value && !isValid) {
                $input.addClass('is-invalid');
                showFieldError($input, 'Invalid material code format. Use: CAT-BRAND-001-CO');
            } else {
                $input.removeClass('is-invalid');
                hideFieldError($input);
            }
        });

        // Price validation
        $('input[name*="mrp"], input[name*="value"], input[name*="price"]').on('input', function() {
            const $input = $(this);
            const value = parseFloat($input.val());
            
            if (value <= 0) {
                $input.addClass('is-invalid');
                showFieldError($input, 'Price must be greater than 0');
            } else {
                $input.removeClass('is-invalid');
                hideFieldError($input);
                
                // Format currency display
                if (value > 0) {
                    const formatted = new Intl.NumberFormat('en-IN', {
                        style: 'currency',
                        currency: 'INR'
                    }).format(value);
                    
                    let $display = $input.siblings('.price-display');
                    if (!$display.length) {
                        $display = $('<div class="price-display mt-1"></div>');
                        $input.after($display);
                    }
                    $display.html(`<span class="price-currency">₹</span> ${value.toLocaleString('en-IN')}`);
                }
            }
        });
    }

    function showFieldError($input, message) {
        let $error = $input.siblings('.invalid-feedback');
        if (!$error.length) {
            $error = $('<div class="invalid-feedback"></div>');
            $input.after($error);
        }
        $error.text(message);
    }

    function hideFieldError($input) {
        $input.siblings('.invalid-feedback').remove();
    }

    // Keyboard Shortcuts
    function addKeyboardShortcuts() {
        $(document).on('keydown', function(e) {
            // Ctrl+S to save
            if (e.ctrlKey && e.keyCode === 83) {
                e.preventDefault();
                $('form').first().submit();
                showToast('Saving...', 'info');
            }
            
            // Ctrl+N for new item
            if (e.ctrlKey && e.keyCode === 78) {
                e.preventDefault();
                const $addLink = $('.btn-success[href*="add"]').first();
                if ($addLink.length) {
                    window.location.href = $addLink.attr('href');
                }
            }
            
            // Escape to cancel/close modals
            if (e.keyCode === 27) {
                $('.modal').modal('hide');
            }
        });
    }

    // Enhanced Stock Displays
    function enhanceStockDisplays() {
        $('td, span').filter(function() {
            const text = $(this).text().trim();
            return /^\d+$/.test(text) && $(this).closest('tr').find('th, td').filter(function() {
                return $(this).text().toLowerCase().includes('stock');
            }).length > 0;
        }).each(function() {
            const $cell = $(this);
            const stock = parseInt($cell.text());
            
            let className = 'stock-high';
            let icon = '✅';
            
            if (stock === 0) {
                className = 'stock-out';
                icon = '❌';
            } else if (stock <= 5) {
                className = 'stock-low';
                icon = '⚠️';
            } else if (stock <= 20) {
                className = 'stock-medium';
                icon = '⚡';
            }
            
            $cell.addClass(className)
                 .html(`${icon} ${stock}`)
                 .attr('title', `Stock level: ${stock} units`);
        });
    }

    // Auto-save functionality
    function addAutoSave() {
        let autoSaveTimeout;
        const AUTOSAVE_DELAY = 30000; // 30 seconds
        
        $('form input, form textarea, form select').on('change input', function() {
            const $form = $(this).closest('form');
            
            // Skip if this is a file input or submit button
            if ($(this).is(':file, :submit, :button')) return;
            
            clearTimeout(autoSaveTimeout);
            autoSaveTimeout = setTimeout(function() {
                saveFormDraft($form);
            }, AUTOSAVE_DELAY);
            
            // Show auto-save indicator
            showAutoSaveIndicator();
        });
    }

    function saveFormDraft($form) {
        const formData = $form.serialize();
        const formId = $form.attr('id') || 'form-' + Date.now();
        
        // Save to localStorage
        localStorage.setItem('draft-' + formId, formData);
        localStorage.setItem('draft-timestamp-' + formId, Date.now());
        
        showToast('Draft saved automatically', 'success', 2000);
    }

    function showAutoSaveIndicator() {
        let $indicator = $('.autosave-indicator');
        if (!$indicator.length) {
            $indicator = $('<div class="autosave-indicator">Auto-saving...</div>');
            $('body').append($indicator);
        }
        
        $indicator.fadeIn().delay(2000).fadeOut();
    }

    // Enhanced Search
    function improveSearch() {
        const $searchInputs = $('input[type="search"], input[name="q"]');
        
        $searchInputs.each(function() {
            const $input = $(this);
            let searchTimeout;
            
            $input.on('input', function() {
                clearTimeout(searchTimeout);
                const query = $input.val();
                
                if (query.length >= 2) {
                    searchTimeout = setTimeout(function() {
                        performSearch(query, $input);
                    }, 500);
                }
            });
        });
    }

    function performSearch(query, $input) {
        // Add search suggestions if available
        // This would connect to your search API
        console.log('Searching for:', query);
    }

    // Confirmation Dialogs
    function addConfirmDialogs() {
        $('.btn-danger, .deletelink').on('click', function(e) {
            e.preventDefault();
            const $link = $(this);
            const action = $link.text().toLowerCase();
            
            showConfirmDialog(
                'Confirm Action',
                `Are you sure you want to ${action}? This action cannot be undone.`,
                'danger',
                function() {
                    if ($link.is('form')) {
                        $link.submit();
                    } else {
                        window.location.href = $link.attr('href');
                    }
                }
            );
        });
    }

    function showConfirmDialog(title, message, type, onConfirm) {
        const modal = $(`
            <div class="modal fade" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-${type}" id="confirm-action">Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(modal);
        modal.modal('show');
        
        modal.find('#confirm-action').on('click', function() {
            modal.modal('hide');
            onConfirm();
        });
        
        modal.on('hidden.bs.modal', function() {
            modal.remove();
        });
    }

    // Enhanced Price Fields
    function enhancePriceFields() {
        $('input[name*="price"], input[name*="mrp"], input[name*="value"]').each(function() {
            const $input = $(this);
            
            // Add currency symbol
            if (!$input.prev('.input-group-text').length) {
                $input.wrap('<div class="input-group"></div>')
                     .before('<span class="input-group-text">₹</span>');
            }
            
            // Format on blur
            $input.on('blur', function() {
                const value = parseFloat($input.val());
                if (!isNaN(value)) {
                    $input.val(value.toFixed(2));
                }
            });
        });
    }

    // Dashboard Animations
    function addDashboardAnimations() {
        // Animate dashboard cards on load
        $('.info-box').each(function(index) {
            $(this).delay(index * 100).animate({
                opacity: 1,
                transform: 'translateY(0)'
            }, 500);
        });
        
        // Animate charts and statistics
        $('.progress-bar').each(function() {
            const $bar = $(this);
            const width = $bar.attr('aria-valuenow');
            $bar.animate({ width: width + '%' }, 1000);
        });
    }

    // Toast Notifications
    function showToast(message, type = 'info', duration = 5000) {
        const toast = $(`
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `);
        
        let $container = $('.toast-container');
        if (!$container.length) {
            $container = $('<div class="toast-container position-fixed top-0 end-0 p-3"></div>');
            $('body').append($container);
        }
        
        $container.append(toast);
        toast.toast({ delay: duration }).toast('show');
        
        toast.on('hidden.bs.toast', function() {
            toast.remove();
        });
    }

    // Utility Functions
    window.SpeisekamarAdmin = {
        showToast: showToast,
        showConfirmDialog: showConfirmDialog,
        showLoadingOverlay: showLoadingOverlay,
        hideLoadingOverlay: hideLoadingOverlay
    };

})(django.jQuery || jQuery);