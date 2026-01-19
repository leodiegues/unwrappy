*[Result]: A type representing either success (Ok) or failure (Err)
*[Option]: A type representing an optional value: Some(value) or Nothing
*[Ok]: The success variant of Result, containing a value
*[Err]: The error variant of Result, containing an error
*[Some]: The present variant of Option, containing a value
*[Nothing]: The absent variant of Option (singleton)
*[LazyResult]: Deferred execution wrapper for async Result chains
*[LazyOption]: Deferred execution wrapper for async Option chains
*[combinator]: A method that transforms or chains Result/Option values
*[unwrap]: Extract the inner value, raising an error if the variant doesn't match
*[pattern matching]: Python 3.10+ structural pattern matching (match/case)
