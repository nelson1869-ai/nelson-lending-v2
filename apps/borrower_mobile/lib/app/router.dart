import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/activation/presentation/activation_screen.dart';
import '../features/auth/domain/auth_state.dart';
import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/home/presentation/splash_screen.dart';
import '../features/registration/presentation/registration_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authNotifier = RouterNotifier(ref);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: authNotifier,
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final status = authState.status;
      final location = state.uri.path;

      if (status == AuthStatus.initial) {
        return location == '/' ? null : '/';
      }

      final isPublicRoute = location == '/login' ||
          location == '/register' ||
          location == '/activation';

      if (status == AuthStatus.unauthenticated) {
        if (isPublicRoute) return null;
        return '/login';
      }

      if (status == AuthStatus.authenticated) {
        if (isPublicRoute || location == '/') return '/home';
        return null;
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegistrationScreen(),
      ),
      GoRoute(
        path: '/activation',
        builder: (context, state) => const ActivationScreen(),
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

class RouterNotifier extends ChangeNotifier {
  final Ref _ref;

  RouterNotifier(this._ref) {
    _ref.listen<AuthState>(
      authControllerProvider,
      (_, __) => notifyListeners(),
    );
  }
}
