import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:borrower_mobile/features/activation/presentation/activation_screen.dart';

void main() {
  testWidgets('ActivationScreen renders activation form elements',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: ActivationScreen(),
        ),
      ),
    );

    expect(find.text('Activate Your Account'), findsOneWidget);
    expect(find.text('Mobile Phone Number'), findsOneWidget);
    expect(find.text('6-Digit Activation Code'), findsOneWidget);
    expect(find.text('Create 6-Digit PIN'), findsOneWidget);
    expect(find.text('Confirm 6-Digit PIN'), findsOneWidget);
    expect(find.text('Activate Account'), findsOneWidget);
  });

  testWidgets('ActivationScreen shows error when PINs do not match',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: ActivationScreen(),
        ),
      ),
    );

    await tester.enterText(
        find.widgetWithText(TextFormField, 'Mobile Phone Number'),
        '+639171234567');
    await tester.enterText(
        find.widgetWithText(TextFormField, '6-Digit Activation Code'),
        '123456');
    await tester.enterText(
        find.widgetWithText(TextFormField, 'Create 6-Digit PIN'), '123456');
    await tester.enterText(
        find.widgetWithText(TextFormField, 'Confirm 6-Digit PIN'), '654321');

    await tester.tap(find.text('Activate Account'));
    await tester.pump();

    expect(find.text('PINs do not match'), findsOneWidget);
  });
}
