// Pine Script syntax highlighting for CodeMirror
(function() {
    // Pine Script mode definition
    CodeMirror.defineMode('pinescript', function() {
        var keywords = {
            'and': 'keyword',
            'or': 'keyword',
            'not': 'keyword',
            'if': 'keyword',
            'else': 'keyword',
            'for': 'keyword',
            'to': 'keyword',
            'by': 'keyword',
            'while': 'keyword',
            'var': 'keyword',
            'varip': 'keyword',
            'switch': 'keyword',
            'case': 'keyword',
            'default': 'keyword'
        };

        var builtinFuncs = {
            'sma': 'builtin',
            'ema': 'builtin',
            'rma': 'builtin',
            'wma': 'builtin',
            'vwma': 'builtin',
            'rsi': 'builtin',
            'macd': 'builtin',
            'crossover': 'builtin',
            'crossunder': 'builtin',
            'highest': 'builtin',
            'lowest': 'builtin',
            'valuewhen': 'builtin',
            'change': 'builtin',
            'ta': 'builtin',
            'strategy': 'keyword',
            'indicator': 'keyword',
            'study': 'keyword',
            'input': 'keyword',
            'plot': 'keyword',
            'plotshape': 'keyword',
            'plotshape': 'keyword',
            'hline': 'keyword',
            'bgcolor': 'keyword'
        };

        var operators = /[+\-*\/%=<>!&|^~?:]/;

        function tokenBase(stream, state) {
            if (stream.eatSpace()) return null;

            var ch = stream.next();

            // Comments
            if (ch === '/' && stream.eat('/')) {
                stream.skipToEnd();
                return 'comment';
            }
            if (ch === '/' && stream.eat('*')) {
                state.tokenize.push(tokenComment);
                return 'comment';
            }

            // Strings
            if (ch === '"' || ch === "'") {
                state.tokenize.push(tokenString(ch));
                return 'string';
            }

            // Numbers
            if (/[\d.]/.test(ch)) {
                stream.eatWhile(/[\d.]/);
                if (stream.eat(/[eE]/)) {
                    stream.eat(/[+\-]/);
                    stream.eatWhile(/[\d]/);
                }
                return 'number';
            }

            // Operators and brackets
            if (operators.test(ch)) {
                return 'operator';
            }
            if (/[{}()\[\]]/.test(ch)) {
                return 'bracket';
            }

            // Words (keywords, builtins, identifiers)
            stream.eatWhile(/[\w$]/);
            var word = stream.current();

            // Check for builtin functions with dots (e.g., ta.sma)
            if (stream.peek() === '.') {
                return 'builtin';
            }

            if (builtinFuncs.hasOwnProperty(word)) {
                return 'builtin';
            }
            if (keywords.hasOwnProperty(word)) {
                return 'keyword';
            }

            return 'variable';
        }

        function tokenString(quote) {
            return function(stream, state) {
                var escaped = false, ch;
                while ((ch = stream.next()) != null) {
                    if (ch === quote && !escaped) break;
                    escaped = ch === '\\';
                }
                if (!escaped) stream.eat(quote);
                return 'string';
            };
        }

        function tokenComment(stream, state) {
            var ch;
            while ((ch = stream.next()) != null) {
                if (ch === '*' && stream.peek() === '/') {
                    stream.next();
                    state.tokenize.pop();
                    break;
                }
            }
            return 'comment';
        }

        return {
            startState: function() {
                return { tokenize: [] };
            },
            token: function(stream, state) {
                if (stream.peek() === '"' || stream.peek() === "'") {
                    state.tokenize.push(tokenString(stream.next()));
                }
                return tokenBase(stream, state);
            }
        };
    });

    // CodeMirror mode for Pine Script
    CodeMirror.defineMIME('text/x-pinescript', 'pinescript');
})();
