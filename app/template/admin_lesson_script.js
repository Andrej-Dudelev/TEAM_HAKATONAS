<script>
document.addEventListener('DOMContentLoaded', () => {
    const validationFieldsContainer = document.getElementById('validation-fields');
    const validationTypeSelector = document.getElementById('validationType');
    
    const startingCodeTextarea = document.getElementById('startingCode');
    const lessonContentTextarea = document.getElementById('lessonContent');

    // Initialize CodeMirror for the starter code textarea
    if (startingCodeTextarea) {
        const codeEditorInstance = CodeMirror.fromTextArea(startingCodeTextarea, {
            lineNumbers: true,
            mode: 'python',
            theme: 'material-darker',
            indentUnit: 4
        });
        codeEditorInstance.on('change', () => {
            startingCodeTextarea.value = codeEditorInstance.getValue();
        });
        setTimeout(() => codeEditorInstance.refresh(), 100);
    }

    // Initialize CodeMirror for the lesson content (Markdown) textarea
    if (lessonContentTextarea) {
        const contentEditorInstance = CodeMirror.fromTextArea(lessonContentTextarea, {
            lineNumbers: true,
            mode: 'markdown',
            theme: 'material-darker',
            lineWrapping: true
        });
        contentEditorInstance.on('change', () => {
            lessonContentTextarea.value = contentEditorInstance.getValue();
        });
        setTimeout(() => contentEditorInstance.refresh(), 100);
    }

    const baseInputClasses = "appearance-none w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg shadow-sm text-gray-200 placeholder-gray-500 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500";

    const fieldTemplates = {
        expected: `
            <div>
                <label for="expectedOutput" class="label">Expected Output</label>
                <textarea id="expectedOutput" class="${baseInputClasses} font-mono" rows="3"></textarea>
            </div>`,
        function_call: `
            <div class="space-y-3">
                <div>
                    <label for="functionName" class="label">Function Name</label>
                    <input type="text" id="functionName" class="${baseInputClasses} font-mono" placeholder="e.g., add_numbers">
                </div>
                <div>
                    <label for="functionArgs" class="label">Arguments (as JSON array)</label>
                    <input type="text" id="functionArgs" class="${baseInputClasses} font-mono" placeholder='e.g., [2, 3]'>
                </div>
                <div>
                    <label for="expectedOutput" class="label">Expected Return Value</label>
                    <input type="text" id="expectedOutput" class="${baseInputClasses} font-mono" placeholder='e.g., 5'>
                </div>
            </div>`
    };

    window.handleValidationChange = function() {
        const selectedType = validationTypeSelector.value;
        validationFieldsContainer.innerHTML = ''; // Clear previous fields

        switch (selectedType) {
            case 'exact_match':
            case 'contains':
                validationFieldsContainer.innerHTML = fieldTemplates.expected;
                break;
            case 'function_call':
                validationFieldsContainer.innerHTML = fieldTemplates.function_call;
                break;
        }
    }

    window.buildValidationCriteria = function() {
        const type = validationTypeSelector.value;
        if (type === 'none' || !type) {
            return null;
        }

        const criteria = { type };
        
        if (type === 'exact_match' || type === 'contains') {
            criteria.expected = document.getElementById('expectedOutput')?.value || '';
        } else if (type === 'function_call') {
            criteria.function_name = document.getElementById('functionName')?.value || '';
            const argsStr = document.getElementById('functionArgs')?.value || '[]';
            try {
                criteria.args = JSON.parse(argsStr);
            } catch(e) {
                console.error("Invalid JSON for function arguments:", e);
                alert("The 'Arguments' field contains invalid JSON. Please correct it.");
                criteria.args = [];
            }
            
            const expectedVal = document.getElementById('expectedOutput')?.value || '';
            try {
                criteria.expected = JSON.parse(expectedVal);
            } catch(e) {
                criteria.expected = expectedVal;
            }
        }
        return criteria;
    }

    window.populateValidationFields = function(criteria) {
        if (!criteria || !criteria.type) {
            validationTypeSelector.value = 'none';
        } else {
            validationTypeSelector.value = criteria.type;
        }
        
        handleValidationChange(); // Create the correct fields

        if (criteria) {
            if (criteria.type === 'exact_match' || criteria.type === 'contains') {
                if(document.getElementById('expectedOutput')) {
                    document.getElementById('expectedOutput').value = criteria.expected || '';
                }
            } else if (criteria.type === 'function_call') {
                if(document.getElementById('functionName')) {
                    document.getElementById('functionName').value = criteria.function_name || '';
                }
                if(document.getElementById('functionArgs')) {
                    document.getElementById('functionArgs').value = JSON.stringify(criteria.args || []);
                }
                if(document.getElementById('expectedOutput')) {
                    let expected = criteria.expected;
                    if(typeof expected !== 'string') {
                        expected = JSON.stringify(expected);
                    }
                    document.getElementById('expectedOutput').value = expected;
                }
            }
        }
    }

    if (validationTypeSelector) {
        validationTypeSelector.addEventListener('change', handleValidationChange);
    }
});
</script>

