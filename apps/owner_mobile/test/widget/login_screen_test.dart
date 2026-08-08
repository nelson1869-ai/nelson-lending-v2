import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/app/theme.dart';
import 'package:owner_mobile/features/auth/presentation/login_screen.dart';

void main() {
  group('LoginScreen Widget Tests', () {
    Widget buildSubject() {
      return ProviderScope(
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: const LoginScreen(),
        ),
      );
    }

    testWidgets('renders login form elements', (WidgetTester tester) async {
      await tester.pumpWidget(buildSubject());

      expect(find.text('Owner Sign In'), findsOneWidget);
      expect(find.byType(TextFormField), findsNWidgets(2));
      expect(find.text('Username'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.widgetWithText(ElevatedButton, 'Sign In'), findsOneWidget);
    });

    testWidgets('shows validation errors when fields are empty',
        (WidgetTester tester) async {
      await tester.pumpWidget(buildSubject());

      await tester.tap(find.widgetWithText(ElevatedButton, 'Sign In'));
      await tester.pump();

      expect(find.text('Please enter username'), findsOneWidget);
      expect(find.text('Please enter password'), findsOneWidget);
    });

    testWidgets('toggles password visibility when icon is pressed',
        (WidgetTester tester) async {
      await tester.pumpWidget(buildSubject());

      final passwordFinder = find.byType(TextFormField).at(1);
      final TextField textFieldBefore = tester.widget(find.descendant(
        of: passwordFinder,
        matching: find.byType(TextField),
      ));

      expect(textFieldBefore.obscureText, isTrue);

      await tester.tap(find.byIcon(Icons.visibility_off));
      await tester.pump();

      final TextField textFieldAfter = tester.widget(find.descendant(
        of: passwordFinder,
        matching: find.byType(TextField),
      ));

      expect(textFieldAfter.obscureText, isFalse);
    });
  });
}
