import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/domain/auth_state.dart';
import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/home/presentation/splash_screen.dart';

/// Listenable adapter that triggers GoRouter re-evaluation when AuthState changes.
class RouterNotifier extends ChangeNotifier {
  final Ref _ref;

  RouterNotifier(this._ref) {
    _ref.listen<AuthState>(
      authControllerProvider,
      (_, __) => notifyListeners(),
    );
  }

  String? redirect(BuildContext context, GoRouterState state) {
    final authState = _ref.read(authControllerProvider);
    final status = authState.status;
    final isLoggingIn = state.matchedLocation == '/login';
    final isSplash = state.matchedLocation == '/';

    // Startup / restoration in progress -> show splash, don't flash login
    if (status == AuthStatus.initial) {
      return isSplash ? null : '/';
    }

    // Unauthenticated -> force /login
    if (status == AuthStatus.unauthenticated || status == AuthStatus.authenticating) {
      return isLoggingIn ? null : '/login';
    }

    // Authenticated -> redirect away from /login and splash to /home
    if (status == AuthStatus.authenticated) {
      if (isLoggingIn || isSplash) {
        return '/home';
      }
    }

    return null;
  }
}

final routerNotifierProvider = Provider<RouterNotifier>((ref) {
  return RouterNotifier(ref);
});

final routerProvider = Provider<GoRouter>((ref) {
  final notifier = ref.watch(routerNotifierProvider);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: notifier,
    redirect: notifier.redirect,
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
    ],
  );
});
