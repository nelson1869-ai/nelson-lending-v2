import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/features/loan_requests/domain/owner_loan_request_models.dart';
import 'package:owner_mobile/features/loan_requests/presentation/owner_loan_request_detail_screen.dart';

void main() {
  group('Owner Loan Requests Review UI Tests', () {
    testWidgets(
        'OwnerLoanRequestDetailScreen displays borrower details and actions for pending request',
        (tester) async {
      tester.view.physicalSize = const Size(320, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      const quote = OwnerLoanQuotePreviewModel(
        principal: 5000.0,
        monthlyRate: 0.05,
        termMonths: 2,
        paymentFrequency: 'monthly',
        firstDueDate: '2026-10-01',
        numberOfPayments: 2,
        periodicPayment: 2688.10,
        totalInterest: 376.20,
        totalAmount: 5376.20,
        schedule: [
          OwnerScheduleItemModel(
            paymentNumber: 1,
            dueDate: '2026-10-01',
            paymentAmount: 2688.10,
            interestPaid: 250.0,
            principalPaid: 2438.10,
            remainingPrincipal: 2561.90,
          ),
        ],
      );

      const model = OwnerLoanRequestDetailModel(
        id: 'req-999',
        borrowerId: 'b-999',
        requestedPrincipal: 5000.0,
        requestedMonthlyRate: 0.05,
        requestedTermMonths: 2,
        requestedPaymentFrequency: 'monthly',
        requestedFirstDueDate: '2026-10-01',
        status: 'pending',
        submittedAt: '2026-08-08T14:00:00Z',
        createdAt: '2026-08-08T14:00:00Z',
        updatedAt: '2026-08-08T14:00:00Z',
        borrowerFirstName: 'Juan',
        borrowerLastName: 'Dela Cruz',
        borrowerNationalId: 'PH-ID-12345',
        borrowerPhoneNumber: '+639171112222',
        quotePreview: quote,
      );

      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: OwnerLoanRequestDetailScreen(request: model),
          ),
        ),
      );

      expect(find.text('Loan Request Review'), findsOneWidget);
      expect(find.text('Juan Dela Cruz'), findsOneWidget);
      expect(find.text('PH-ID-12345'), findsOneWidget);
      expect(find.text('Approve'), findsOneWidget);
      expect(find.text('Reject'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
