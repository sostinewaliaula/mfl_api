import json

from django.contrib.auth.models import AnonymousUser

from rest_framework import generics
from rest_framework import status
from rest_framework.views import Response, APIView

from common.views import AuditableDetailViewMixin
from common.utilities import CustomRetrieveUpdateDestroyView
from common.models import ContactType


from ..models import (
    Facility,
    FacilityUnit,
    OfficerContact,
    Owner,
    FacilityContact,
    FacilityOfficer,
    FacilityUnitRegulation,
    KephLevel,
    OptionGroup,
    FacilityLevelChangeReason,
    FacilityUpdates,
    Service,
    Option,
    RegulatingBody,
    JobTitle
)

from ..serializers import (
    FacilitySerializer,
    FacilityUnitSerializer,
    OfficerContactSerializer,
    OwnerSerializer,
    FacilityListSerializer,
    FacilityDetailSerializer,
    FacilityContactSerializer,
    FacilityOfficerSerializer,
    FacilityUnitRegulationSerializer,
    KephLevelSerializer,
    OptionGroupSerializer,
    CreateFacilityOfficerMixin,
    FacilityLevelChangeReasonSerializer
)

from ..filters import (
    FacilityFilter,
    FacilityUnitFilter,
    OfficerContactFilter,
    OwnerFilter,
    FacilityContactFilter,
    FacilityOfficerFilter,
    FacilityUnitRegulationFilter,
    KephLevelFilter,
    OptionGroupFilter,
    FacilityLevelChangeReasonFilter

)

from ..utils import (
    _validate_services,
    _validate_units,
    _validate_contacts,
    _officer_data_is_valid
)


class QuerysetFilterMixin(object):
    """
    Filter that only allows users to list facilities in their county
    if they are not a national user.

    This complements the fairly standard ( django.contrib.auth )
    permissions setup.

    It is not intended to be applied to all views ( it should be used
    only on views for resources that are directly linked to counties
    e.g. facilities ).
    """
    def get_queryset(self, *args, **kwargs):
        # The line below reflects the fact that geographic "attachment"
        # will occur at the smallest unit i.e the ward
        # return self.queryset
        # nairobi = County.objects.get(code=47)

        # return self.queryset
        if not isinstance(self.request.user, AnonymousUser):
            if not self.request.user.is_national and \
                    self.request.user.county \
                    and hasattr(self.queryset.model, 'ward'):
                self.queryset = self.queryset.filter(
                    ward__constituency__county=self.request.user.county)

            elif self.request.user.regulator and hasattr(
                    self.queryset.model, 'regulatory_body'):
                self.queryset = self.queryset.filter(
                    regulatory_body=self.request.user.regulator)
            elif self.request.user.is_national and not \
                    self.request.user.county:
                self.queryset = self.queryset
            elif self.request.user.constituency and hasattr(
                    self.queryset.model, 'ward'):
                self.queryset = self.queryset.filter(
                    ward__constituency=self.request.user.constituency)
            else:
                self.queryset = self.queryset
        else:
            self.queryset = self.queryset

        if self.request.user.has_perm("facilities.view_unpublished_facilities") \
            is False and 'is_published' in [
                field.name for field in
                self.queryset.model._meta.get_fields()]:

            self.queryset = self.queryset.filter(is_published=True)

        if self.request.user.has_perm(
            "facilities.view_unapproved_facilities") \
            is False and 'approved' in [
                field.name for field in
                self.queryset.model._meta.get_fields()]:
            self.queryset = self.queryset.filter(approved=True)

        if self.request.user.has_perm(
                "facilities.view_classified_facilities") \
            is False and 'is_classified' in [
                field.name for field in
                self.queryset.model._meta.get_fields()]:
            self.queryset = self.queryset.filter(is_classified=False)

        if self.request.user.has_perm("facilities.view_rejected_facilities") \
            is False and ('rejected' in [
                field.name for field in
                self.queryset.model._meta.get_fields()]):
            self.queryset = self.queryset.filter(rejected=False)

        if self.request.user.has_perm(
            "facilities.view_closed_facilities") is False and \
            'closed' in [field.name for field in
                         self.queryset.model._meta.get_fields()]:
            self.queryset = self.queryset.filter(closed=False)

        return self.queryset


class FacilityLevelChangeReasonListView(generics.ListCreateAPIView):
    """
    Lists and creates the  generic upgrade and down grade reasons
    reason --   A reason for  upgrade or downgrade
    description -- Description the reason
    Created --  Date the record was Created
    Updated -- Date the record was Updated
    Created_by -- User who created the record
    Updated_by -- User who updated the record
    active  -- Boolean is the record active
    deleted -- Boolean is the record deleted
    """
    queryset = FacilityLevelChangeReason.objects.all()
    filter_class = FacilityLevelChangeReasonFilter
    serializer_class = FacilityLevelChangeReasonSerializer
    ordering_fields = ('reason', 'description', 'is_upgrade_reason')


class FacilityLevelChangeReasonDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    """
    Retrieves a single facility level change reason
    """
    queryset = FacilityLevelChangeReason.objects.all()
    serializer_class = FacilityLevelChangeReasonSerializer


class KephLevelListView(generics.ListCreateAPIView):
    """
    Lists and creates the  Kenya Essential Package for health (KEPH)
    name -- Name of a level 1
    description -- Description the KEPH
    Created --  Date the record was Created
    Updated -- Date the record was Updated
    Created_by -- User who created the record
    Updated_by -- User who updated the record
    active  -- Boolean is the record active
    deleted -- Boolean is the record deleted
    """
    queryset = KephLevel.objects.all()
    filter_class = KephLevelFilter
    serializer_class = KephLevelSerializer
    ordering_fields = ('name', 'value', 'description')


class KephLevelDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    """
    Retrieves a single KEPH level
    """
    queryset = KephLevel.objects.all()
    serializer_class = KephLevelSerializer


class FacilityUnitsListView(generics.ListCreateAPIView):
    """
    Lists and creates facility units

    facility -- A facility's pk
    name -- Name of a facility unit
    description -- Description of a facility unit
    Created --  Date the record was Created
    Updated -- Date the record was Updated
    Created_by -- User who created the record
    Updated_by -- User who updated the record
    active  -- Boolean is the record active
    deleted -- Boolean is the record deleted
    """
    queryset = FacilityUnit.objects.all()
    serializer_class = FacilityUnitSerializer
    ordering_fields = ('name', 'facility', 'regulating_body',)
    filter_class = FacilityUnitFilter


class FacilityUnitDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    """
    Retrieves a particular facility unit's detail
    """
    queryset = FacilityUnit.objects.all()
    serializer_class = FacilityUnitSerializer


class OfficerContactListView(generics.ListCreateAPIView):
    """
    Lists and creates officer contacts

    officer -- An officer's pk
    contact --  A contacts pk
    Created --  Date the record was Created
    Updated -- Date the record was Updated
    Created_by -- User who created the record
    Updated_by -- User who updated the record
    active  -- Boolean is the record active
    deleted -- Boolean is the record deleted
    """
    queryset = OfficerContact.objects.all()
    serializer_class = OfficerContactSerializer
    ordering_fields = ('officer', 'contact',)
    filter_class = OfficerContactFilter


class OfficerContactDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    """
    Retrieves a particular officer contact detail
    """
    queryset = OfficerContact.objects.all()
    serializer_class = OfficerContactSerializer


class OwnerListView(generics.ListCreateAPIView):
    """
    List and creates a list of owners

    name -- The name of an owner
    description -- The description of an owner
    abbreviation -- The abbreviation of an owner
    code --  The code of an owner
    owner_type -- An owner-type's pk
    Created --  Date the record was Created
    Updated -- Date the record was Updated
    Created_by -- User who created the record
    Updated_by -- User who updated the record
    active  -- Boolean is the record active
    deleted -- Boolean is the record deleted
    """
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    filter_class = OwnerFilter
    ordering_fields = ('name', 'code', 'owner_type',)


class OwnerDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    """
    Retrieves a particular owner's details
    """
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer


class FacilityListView(QuerysetFilterMixin, generics.ListCreateAPIView):
    """
    Lists and creates facilities

    name -- The name of the facility<br>
    code -- A list of comma separated facility codes (one or more)<br>
    description -- The description of the facility<br>
    facility_type -- A list of comma separated facility type's pk<br>
    operation_status -- A list of comma separated operation statuses pks<br>
    ward -- A list of comma separated ward pks (one or more)<br>
    ward_code -- A list of comma separated ward codes<br>
    county_code -- A list of comma separated county codes<br>
    constituency_code -- A list of comma separated constituency codes<br>
    county -- A list of comma separated county pks<br>
    constituency -- A list of comma separated constituency pks<br>
    owner -- A list of comma separated owner pks<br>
    number_of_beds -- A list of comma separated integers<br>
    number_of_cots -- A list of comma separated integers<br>
    open_whole_day -- Boolean True/False<br>
    is_classified -- Boolean True/False<br>
    is_published -- Boolean True/False<br>
    is_regulated -- Boolean True/False<br>
    service_category -- A service category's pk<br>
    Created --  Date the record was Created<br>
    Updated -- Date the record was Updated<br>
    Created_by -- User who created the record<br>
    Updated_by -- User who updated the record<br>
    active  -- Boolean is the record active<br>
    deleted -- Boolean is the record deleted<br>
    """
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer
    filter_class = FacilityFilter
    ordering_fields = (
        'name', 'code', 'number_of_beds', 'number_of_cots',
        'operation_status', 'ward', 'owner',
    )


class FacilityListReadOnlyView(QuerysetFilterMixin, generics.ListAPIView):
    """
    Returns a slimmed payload of the facility.
    """
    queryset = Facility.objects.all()
    serializer_class = FacilityListSerializer
    filter_class = FacilityFilter
    ordering_fields = (
        'code', 'name', 'county', 'constituency', 'facility_type_name',
        'owner_type_name', 'is_published'
    )


class FacilityDetailView(
        QuerysetFilterMixin, AuditableDetailViewMixin,
        generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieves a particular facility
    """
    queryset = Facility.objects.all()
    serializer_class = FacilityDetailSerializer
    validation_errors = {}

    def buffer_contacts(self, update, contacts):
        """
        Prepares the new facility contacts to be saved in the facility
        updates model
        """
        if update.contacts and update.contacts != 'null':
            proposed_contacts = json.loads(update.contacts)
            update.contacts = json.dumps(proposed_contacts + contacts)
        else:
            update.contacts = json.dumps(contacts)

    def buffer_services(self, update, services):
        """
        Prepares the new facility services to be saved in the facility
        updates model
        """
        if update.services and update.services != 'null':
            proposed_services = json.loads(update.services)
            update.services = json.dumps(proposed_services + services)
        else:
            update.services = json.dumps(services)

    def buffer_units(self, update, units):
        """
        Prepares the new facility units(departments) to be saved in the
        facility updates model
        """
        if update.units and update.units != 'null':
            proposed_units = json.loads(update.units)
            update.units = json.dumps(proposed_units + units)
        else:
            update.units = json.dumps(units)

    def populate_service_name(self, services):
        """
        Resolves and updates the service names and option display_name
        """
        for service in services:
            id = service.get('service')
            obj = Service.objects.get(id=id)
            service['name'] = obj.name
            option = service.get('option', None)
            if option:
                service['display_name'] = Option.objects.get(
                    id=option).display_text
        return services

    def populate_contact_type_names(self, contacts):
        """
        Resolves and populates the contact type names
        """
        for contact in contacts:
            contact['contact_type_name'] = ContactType.objects.get(
                id=contact.get('contact_type')).name
        return contacts

    def populate_regulatory_body_names(self, units):
        """
        Resolves and populates the regulatory body names
        """
        for unit in units:
            unit['regulating_body_name'] = RegulatingBody.objects.get(
                id=unit['regulating_body']).name
        return units

    def populate_officer_incharge_contacts(self, officer_in_charge):
        """
        Resolves the contact_type_name for the officer_in_charge contacts
        """
        for contact in officer_in_charge['contacts']:
            contact['contact_type_name'] = ContactType.objects.get(
                id=contact.get('type')).name
        return officer_in_charge

    def populate_officer_incharge_job_title(self, officer_in_charge):
        """
        Resolves the job title name for the officer in-charge
        """
        officer_in_charge['job_title_name'] = JobTitle.objects.get(
            id=officer_in_charge['title']).name
        return officer_in_charge

    def _validate_payload(self, services, contacts, units, officer_in_charge):
        """
        Validates the updated attributes before  buffering them
        """
        service_errors = _validate_services(services)

        if service_errors:
            self.validation_errors.update({"services": service_errors})

        contact_errors = _validate_contacts(contacts)
        if contact_errors:
            self.validation_errors.update({"contacts": contact_errors})

        unit_errors = _validate_units(units)
        if unit_errors:
            self.validation_errors.update({"units": unit_errors})
        officer_errors = _officer_data_is_valid(officer_in_charge)

        if officer_errors and officer_in_charge != {} and officer_errors is \
                not True:
            self.validation_errors.update(
                {"officer_in_charge": officer_errors})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        user_id = request.user
        del user_id
        request.data['updated_by_id'] = request.user.id
        instance = self.get_object()
        self.validation_errors = {}

        services = request.data.pop('services', [])
        contacts = request.data.pop('contacts', [])
        units = request.data.pop('units', [])
        officer_in_charge = request.data.pop(
            'officer_in_charge', {})
        if officer_in_charge:
            officer_in_charge['facility_id'] = str(instance.id)

        self. _validate_payload(services, contacts, units, officer_in_charge)

        if any(self.validation_errors):
            return Response(
                data=self.validation_errors,
                status=status.HTTP_400_BAD_REQUEST)
        if instance.approved:
            try:
                update = FacilityUpdates.objects.filter(
                    facility=instance, cancelled=False, approved=False)[0]
            except IndexError:
                update = FacilityUpdates.objects.create(facility=instance)
            services = self.populate_service_name(services)
            self.buffer_services(update, services)

            contacts = self.populate_contact_type_names(contacts)
            self.buffer_contacts(update, contacts)

            units = self.populate_regulatory_body_names(units)
            self.buffer_units(update, units)

            if officer_in_charge != {}:
                officer_in_charge = self.populate_officer_incharge_contacts(
                    officer_in_charge)
                officer_in_charge = self.populate_officer_incharge_job_title(
                    officer_in_charge)
                update.officer_in_charge = json.dumps(officer_in_charge)
            update.is_new = False
            update.save()
        else:
            request.data['services'] = services
            request.data['contacts'] = contacts
            request.data['units'] = units
            if officer_in_charge != {}:
                request.data['officer_in_charge'] = officer_in_charge

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FacilityContactListView(generics.ListCreateAPIView):
    """
    Lists and creates facility contacts

    facility -- A facility's pk
    contact -- A contact's pk
    Created --  Date the record was Created
    Updated -- Date the record was Updated
    Created_by -- User who created the record
    Updated_by -- User who updated the record
    active  -- Boolean is the record active
    deleted -- Boolean is the record deleted
    """
    queryset = FacilityContact.objects.all()
    serializer_class = FacilityContactSerializer
    filter_class = FacilityContactFilter
    ordering_fields = ('facility', 'contact',)


class FacilityContactDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    """
    Retrieves a particular facility contact
    """
    queryset = FacilityContact.objects.all()
    serializer_class = FacilityContactSerializer


class FacilityOfficerListView(generics.ListCreateAPIView):
    serializer_class = FacilityOfficerSerializer
    queryset = FacilityOfficer.objects.all()
    filter_class = FacilityOfficerFilter
    ordering_fields = (
        'name', 'id_number', 'registration_number',
        'facility_name')


class FacilityOfficerDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    serializer_class = FacilityOfficerSerializer
    queryset = FacilityOfficer.objects.all()


class FacilityUnitRegulationListView(generics.ListCreateAPIView):
    queryset = FacilityUnitRegulation.objects.all()
    serializer_class = FacilityUnitRegulationSerializer
    filter_class = FacilityUnitRegulationFilter
    ordering_fields = ('facility_unit', 'regulation_status')


class FacilityUnitRegulationDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    queryset = FacilityUnitRegulation.objects.all()
    serializer_class = FacilityUnitRegulationSerializer


class CustomFacilityOfficerView(CreateFacilityOfficerMixin, APIView):
    """
    A custom view for creating facility officers.
    Make it less painful to create facility officers via the frontend.
    """

    def post(self, *args, **kwargs):
        data = self.request.data
        self.user = self.request.user
        created_officer = self.create_officer(data)

        if created_officer.get("created") is not True:

            return Response(
                {"detail": created_officer.get("detail")},
                status=status.HTTP_400_BAD_REQUEST)
        else:

            return Response(
                created_officer.get("detail"), status=status.HTTP_201_CREATED)

    def get(self, *args, **kwargs):
        facility = Facility.objects.get(id=kwargs['facility_id'])
        facility_officers = FacilityOfficer.objects.filter(facility=facility)
        serialized_officers = FacilityOfficerSerializer(
            facility_officers, many=True).data
        return Response(serialized_officers)

    def delete(self, *args, **kwargs):
        officer = FacilityOfficer.objects.get(id=kwargs['pk'])
        officer.deleted = True
        officer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OptionGroupListView(generics.ListCreateAPIView):
    queryset = OptionGroup.objects.all()
    serializer_class = OptionGroupSerializer
    filter_class = OptionGroupFilter
    ordering_fields = ('name', )


class OptionGroupDetailView(
        AuditableDetailViewMixin, CustomRetrieveUpdateDestroyView):
    queryset = OptionGroup.objects.all()
    serializer_class = OptionGroupSerializer
