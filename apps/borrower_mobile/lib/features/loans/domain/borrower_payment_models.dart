import 'package:flutter/foundation.dart';

@immutable
class BorrowerPaymentModel {
  final String id;
  final String loanId;
  final String amount;
  final String interestPaid;
  final String principalPaid;
  final String unappliedCredit;
  final String remainingInterest;
  final String remainingPrincipal;
  final String paymentDate;
  final String postedAt;
  final String? reference;

  const BorrowerPaymentModel({
    required this.id,
    required this.loanId,
    required this.amount,
    required this.interestPaid,
    required this.principalPaid,
    required this.unappliedCredit,
    required this.remainingInterest,
    required this.remainingPrincipal,
    required this.paymentDate,
    required this.postedAt,
    this.reference,
  });

  factory BorrowerPaymentModel.fromJson(Map<String, dynamic> json) {
    return BorrowerPaymentModel(
      id: json['id'] as String,
      loanId: json['loanId'] as String,
      amount: json['amount'] as String,
      interestPaid: json['interestPaid'] as String,
      principalPaid: json['principalPaid'] as String,
      unappliedCredit: json['unappliedCredit'] as String,
      remainingInterest: json['remainingInterest'] as String,
      remainingPrincipal: json['remainingPrincipal'] as String,
      paymentDate: json['paymentDate'] as String,
      postedAt: json['postedAt'] as String,
      reference: json['reference'] as String?,
    );
  }
}
