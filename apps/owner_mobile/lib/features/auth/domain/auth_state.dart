import 'owner_profile.dart';

enum AuthStatus {
  initial,
  unauthenticated,
  authenticating,
  authenticated,
}

class AuthState {
  final AuthStatus status;
  final OwnerProfile? owner;
  final String? errorMessage;

  const AuthState({
    required this.status,
    this.owner,
    this.errorMessage,
  });

  const AuthState.initial()
      : status = AuthStatus.initial,
        owner = null,
        errorMessage = null;

  const AuthState.unauthenticated([this.errorMessage])
      : status = AuthStatus.unauthenticated,
        owner = null;

  const AuthState.authenticating()
      : status = AuthStatus.authenticating,
        owner = null,
        errorMessage = null;

  const AuthState.authenticated(this.owner)
      : status = AuthStatus.authenticated,
        errorMessage = null;

  AuthState copyWith({
    AuthStatus? status,
    OwnerProfile? owner,
    String? errorMessage,
  }) {
    return AuthState(
      status: status ?? this.status,
      owner: owner ?? this.owner,
      errorMessage: errorMessage,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AuthState &&
          runtimeType == other.runtimeType &&
          status == other.status &&
          owner?.id == other.owner?.id &&
          errorMessage == other.errorMessage;

  @override
  int get hashCode => status.hashCode ^ owner.hashCode ^ errorMessage.hashCode;
}
