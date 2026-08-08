import 'borrower_profile.dart';

enum AuthStatus {
  initial,
  authenticating,
  authenticated,
  unauthenticated,
}

class AuthState {
  final AuthStatus status;
  final BorrowerProfile? borrower;
  final String? errorMessage;

  const AuthState({
    required this.status,
    this.borrower,
    this.errorMessage,
  });

  const AuthState.initial()
      : status = AuthStatus.initial,
        borrower = null,
        errorMessage = null;

  const AuthState.authenticating()
      : status = AuthStatus.authenticating,
        borrower = null,
        errorMessage = null;

  const AuthState.authenticated(BorrowerProfile profile)
      : status = AuthStatus.authenticated,
        borrower = profile,
        errorMessage = null;

  const AuthState.unauthenticated([String? message])
      : status = AuthStatus.unauthenticated,
        borrower = null,
        errorMessage = message;

  bool get isAuthenticated => status == AuthStatus.authenticated;
}
