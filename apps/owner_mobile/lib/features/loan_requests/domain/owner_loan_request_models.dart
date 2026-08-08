class OwnerScheduleItemModel {
  final int paymentNumber;
  final String dueDate;
  final double paymentAmount;
  final double interestPaid;
  final double principalPaid;
  final double remainingPrincipal;

  const OwnerScheduleItemModel({
    required this.paymentNumber,
    required this.dueDate,
    required this.paymentAmount,
    required this.interestPaid,
    required this.principalPaid,
    required this.remainingPrincipal,
  });

  factory OwnerScheduleItemModel.fromJson(Map<String, dynamic> json) {
    return OwnerScheduleItemModel(
      paymentNumber: (json['paymentNumber'] as num).toInt(),
      dueDate: json['dueDate'] as String,
      paymentAmount: (num.parse(json['paymentAmount'].toString())).toDouble(),
      interestPaid: (num.parse(json['interestPaid'].toString())).toDouble(),
      principalPaid: (num.parse(json['principalPaid'].toString())).toDouble(),
      remainingPrincipal:
          (num.parse(json['remainingPrincipal'].toString())).toDouble(),
    );
  }
}

class OwnerLoanQuotePreviewModel {
  final double principal;
  final double monthlyRate;
  final int termMonths;
  final String paymentFrequency;
  final String firstDueDate;
  final int numberOfPayments;
  final double periodicPayment;
  final double totalInterest;
  final double totalAmount;
  final List<OwnerScheduleItemModel> schedule;

  const OwnerLoanQuotePreviewModel({
    required this.principal,
    required this.monthlyRate,
    required this.termMonths,
    required this.paymentFrequency,
    required this.firstDueDate,
    required this.numberOfPayments,
    required this.periodicPayment,
    required this.totalInterest,
    required this.totalAmount,
    required this.schedule,
  });

  factory OwnerLoanQuotePreviewModel.fromJson(Map<String, dynamic> json) {
    final rawSchedule = json['schedule'] as List<dynamic>? ?? [];
    return OwnerLoanQuotePreviewModel(
      principal: (num.parse(json['principal'].toString())).toDouble(),
      monthlyRate: (num.parse(json['monthlyRate'].toString())).toDouble(),
      termMonths: (json['termMonths'] as num).toInt(),
      paymentFrequency: json['paymentFrequency'] as String,
      firstDueDate: json['firstDueDate'] as String,
      numberOfPayments: (json['numberOfPayments'] as num).toInt(),
      periodicPayment:
          (num.parse(json['periodicPayment'].toString())).toDouble(),
      totalInterest: (num.parse(json['totalInterest'].toString())).toDouble(),
      totalAmount: (num.parse(json['totalAmount'].toString())).toDouble(),
      schedule: rawSchedule
          .map((e) => OwnerScheduleItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class OwnerLoanRequestDetailModel {
  final String id;
  final String borrowerId;
  final double requestedPrincipal;
  final double requestedMonthlyRate;
  final int requestedTermMonths;
  final String requestedPaymentFrequency;
  final String requestedFirstDueDate;
  final String status;
  final String submittedAt;
  final String? reviewedAt;
  final String? reviewedByOwnerId;
  final String? ownerNote;
  final String createdAt;
  final String updatedAt;
  final String borrowerFirstName;
  final String borrowerLastName;
  final String borrowerNationalId;
  final String borrowerPhoneNumber;
  final OwnerLoanQuotePreviewModel quotePreview;

  String get borrowerFullName => '$borrowerFirstName $borrowerLastName';

  const OwnerLoanRequestDetailModel({
    required this.id,
    required this.borrowerId,
    required this.requestedPrincipal,
    required this.requestedMonthlyRate,
    required this.requestedTermMonths,
    required this.requestedPaymentFrequency,
    required this.requestedFirstDueDate,
    required this.status,
    required this.submittedAt,
    this.reviewedAt,
    this.reviewedByOwnerId,
    this.ownerNote,
    required this.createdAt,
    required this.updatedAt,
    required this.borrowerFirstName,
    required this.borrowerLastName,
    required this.borrowerNationalId,
    required this.borrowerPhoneNumber,
    required this.quotePreview,
  });

  factory OwnerLoanRequestDetailModel.fromJson(Map<String, dynamic> json) {
    return OwnerLoanRequestDetailModel(
      id: json['id'] as String,
      borrowerId: json['borrowerId'] as String,
      requestedPrincipal:
          (num.parse(json['requestedPrincipal'].toString())).toDouble(),
      requestedMonthlyRate:
          (num.parse(json['requestedMonthlyRate'].toString())).toDouble(),
      requestedTermMonths: (json['requestedTermMonths'] as num).toInt(),
      requestedPaymentFrequency: json['requestedPaymentFrequency'] as String,
      requestedFirstDueDate: json['requestedFirstDueDate'] as String,
      status: json['status'] as String,
      submittedAt: json['submittedAt'] as String,
      reviewedAt: json['reviewedAt'] as String?,
      reviewedByOwnerId: json['reviewedByOwnerId'] as String?,
      ownerNote: json['ownerNote'] as String?,
      createdAt: json['createdAt'] as String,
      updatedAt: json['updatedAt'] as String,
      borrowerFirstName: json['borrowerFirstName'] as String,
      borrowerLastName: json['borrowerLastName'] as String,
      borrowerNationalId: json['borrowerNationalId'] as String,
      borrowerPhoneNumber: json['borrowerPhoneNumber'] as String,
      quotePreview: OwnerLoanQuotePreviewModel.fromJson(
          json['quotePreview'] as Map<String, dynamic>),
    );
  }
}
